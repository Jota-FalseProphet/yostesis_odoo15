from odoo import Command
from odoo.tests import Form, TransactionCase


class TestPhantomBomExplodeFix(TransactionCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.env = cls.env(context=dict(cls.env.context, tracking_disable=True))

        for table in ("product_template", "product_product"):
            cls.cr.execute(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = %s AND column_name = 'base_unit_count'",
                (table,),
            )
            if cls.cr.fetchone():
                cls.cr.execute(
                    "ALTER TABLE {} ALTER COLUMN base_unit_count SET DEFAULT 0".format(
                        table
                    )
                )

        cls.color_attr = cls.env["product.attribute"].create(
            {"name": "Color", "display_type": "radio", "create_variant": "always"}
        )
        cls.cyan, cls.magenta = cls.env["product.attribute.value"].create(
            [
                {"name": "Cyan", "attribute_id": cls.color_attr.id},
                {"name": "Magenta", "attribute_id": cls.color_attr.id},
            ]
        )

        cls.raw_material_a = cls._create_simple_product("Raw Material A")
        cls.raw_material_b = cls._create_simple_product("Raw Material B")

        cls.kit_template = cls.env["product.template"].create(
            {"name": "Kit Component", "type": "product"}
        )
        cls.env["product.template.attribute.line"].create(
            {
                "attribute_id": cls.color_attr.id,
                "product_tmpl_id": cls.kit_template.id,
                "value_ids": [Command.set(cls.color_attr.value_ids.ids)],
            }
        )

        cls.kit_cyan = cls.kit_template.product_variant_ids.filtered(
            lambda p: cls.cyan in p.product_template_attribute_value_ids.mapped(
                "product_attribute_value_id"
            )
        )
        cls.kit_magenta = cls.kit_template.product_variant_ids.filtered(
            lambda p: cls.magenta in p.product_template_attribute_value_ids.mapped(
                "product_attribute_value_id"
            )
        )

        cls.phantom_bom_cyan = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.kit_template.id,
                "product_id": cls.kit_cyan.id,
                "product_qty": 1.0,
                "type": "phantom",
                "bom_line_ids": [
                    (0, 0, {
                        "product_id": cls.raw_material_a.id,
                        "product_qty": 2.0,
                    }),
                    (0, 0, {
                        "product_id": cls.raw_material_b.id,
                        "product_qty": 3.0,
                    }),
                ],
            }
        )

        cls.parent_template = cls.env["product.template"].create(
            {"name": "Parent Product", "type": "product"}
        )
        cls.env["product.template.attribute.line"].create(
            {
                "attribute_id": cls.color_attr.id,
                "product_tmpl_id": cls.parent_template.id,
                "value_ids": [Command.set(cls.color_attr.value_ids.ids)],
            }
        )
        cls.parent_cyan = cls.parent_template.product_variant_ids.filtered(
            lambda p: cls.cyan in p.product_template_attribute_value_ids.mapped(
                "product_attribute_value_id"
            )
        )

        cls.parent_bom = cls.env["mrp.bom"].create(
            {
                "product_tmpl_id": cls.parent_template.id,
                "product_qty": 1.0,
                "type": "normal",
                "bom_line_ids": [
                    (0, 0, {
                        "component_template_id": cls.kit_template.id,
                        "product_id": cls.kit_cyan.id,
                        "product_qty": 1.0,
                    }),
                ],
            }
        )

    @classmethod
    def _create_simple_product(cls, name):
        tmpl = cls.env["product.template"].create(
            {"name": name, "type": "product"}
        )
        return tmpl.product_variant_ids[:1]

    def test_phantom_explode_with_component_template(self):
        boms_done, lines_done = self.parent_bom.explode(self.parent_cyan, 1)

        line_products = {line.product_id for line, _data in lines_done}
        self.assertIn(
            self.raw_material_a,
            line_products,
            "Raw Material A should appear after exploding the phantom kit",
        )
        self.assertIn(
            self.raw_material_b,
            line_products,
            "Raw Material B should appear after exploding the phantom kit",
        )
        self.assertNotIn(
            self.kit_cyan,
            line_products,
            "The phantom kit product itself should NOT appear in final lines",
        )

    def test_phantom_explode_quantities(self):
        _boms_done, lines_done = self.parent_bom.explode(self.parent_cyan, 2)

        qty_map = {
            line.product_id: data["qty"] for line, data in lines_done
        }
        self.assertEqual(
            qty_map.get(self.raw_material_a),
            4.0,
            "2 parent * 1 kit * 2 raw_a = 4",
        )
        self.assertEqual(
            qty_map.get(self.raw_material_b),
            6.0,
            "2 parent * 1 kit * 3 raw_b = 6",
        )

    def test_non_phantom_component_template_not_exploded(self):
        self.phantom_bom_cyan.type = "normal"

        _boms_done, lines_done = self.parent_bom.explode(self.parent_cyan, 1)

        line_products = {line.product_id for line, _data in lines_done}
        self.assertIn(
            self.kit_cyan,
            line_products,
            "Non-phantom component should remain as-is in the lines",
        )
        self.assertNotIn(
            self.raw_material_a,
            line_products,
            "Raw materials should NOT appear for a non-phantom BOM",
        )

    def test_manufacturing_order_with_phantom_component_template(self):
        mo_form = Form(self.env["mrp.production"])
        mo_form.product_id = self.parent_cyan
        mo_form.bom_id = self.parent_bom
        mo_form.product_qty = 1
        mo = mo_form.save()
        mo.action_confirm()

        raw_products = mo.move_raw_ids.mapped("product_id")
        self.assertIn(
            self.raw_material_a,
            raw_products,
            "MO should have Raw Material A from phantom kit explosion",
        )
        self.assertIn(
            self.raw_material_b,
            raw_products,
            "MO should have Raw Material B from phantom kit explosion",
        )
        self.assertNotIn(
            self.kit_cyan,
            raw_products,
            "Phantom kit product should not be in MO raw materials",
        )
