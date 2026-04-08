import logging
from collections import defaultdict

from odoo import _, models
from odoo.exceptions import UserError
from odoo.tools import float_round

_log = logging.getLogger(__name__)


class MrpBom(models.Model):
    _inherit = "mrp.bom"

    def _get_component_template_product(
        self, bom_line, bom_product_id, line_product_id
    ):
        if bom_line.component_template_id:
            comp = bom_line.component_template_id
            comp_attr_ids = (
                comp.valid_product_template_attribute_line_ids.attribute_id.ids
            )
            prod_attr_ids = (
                bom_product_id.valid_product_template_attribute_line_ids.attribute_id.ids
            )
            if not all(item in prod_attr_ids for item in comp_attr_ids):
                return False
            ptavs = bom_product_id.product_template_attribute_value_ids
            combination = self.env["product.template.attribute.value"].search([
                ("product_tmpl_id", "=", comp.id),
                ("product_attribute_value_id", "in",
                 ptavs.mapped("product_attribute_value_id").ids),
            ])
            if not combination:
                return False
            product_id = comp._get_variant_for_combination(combination)
            if product_id and product_id.active:
                return product_id
            return False
        else:
            return line_product_id

    def explode(self, product, quantity, picking_type=False):
        self = self.with_context(prefetch_fields=False)

        graph = defaultdict(list)
        V = set()

        def check_cycle(v, visited, recStack, graph):
            visited[v] = True
            recStack[v] = True
            for neighbour in graph[v]:
                if visited[neighbour] is False:
                    if check_cycle(neighbour, visited, recStack, graph) is True:
                        return True
                elif recStack[neighbour] is True:
                    return True
            recStack[v] = False
            return False

        product_ids = set()
        product_boms = {}

        def update_product_boms():
            products = self.env["product.product"].with_context(
                prefetch_fields=False
            ).browse(product_ids)
            product_boms.update(
                self._bom_find(
                    products,
                    bom_type="phantom",
                    picking_type=picking_type or self.picking_type_id,
                    company_id=self.company_id.id,
                )
            )
            for prod in products:
                product_boms.setdefault(prod, self.env["mrp.bom"])

        boms_done = [
            (
                self,
                {
                    "qty": quantity,
                    "product": product,
                    "original_qty": quantity,
                    "parent_line": False,
                },
            )
        ]
        lines_done = []
        V |= {product.product_tmpl_id.id}

        bom_lines = []
        for bom_line in self.bom_line_ids:
            product_id = bom_line.product_id
            if product_id:
                V |= {product_id.product_tmpl_id.id}
                graph[product.product_tmpl_id.id].append(
                    product_id.product_tmpl_id.id
                )
                product_ids.add(product_id.id)
            bom_lines.append((bom_line, product, quantity, False))
        update_product_boms()
        product_ids.clear()

        while bom_lines:
            current_line, current_product, current_qty, parent_line = bom_lines[0]
            bom_lines = bom_lines[1:]

            if current_line._skip_bom_line(current_product):
                continue

            line_quantity = current_qty * current_line.product_qty

            resolved_product = self._get_component_template_product(
                current_line, current_product, current_line.product_id
            )
            if not resolved_product:
                continue

            if resolved_product not in product_boms:
                product_ids.add(resolved_product.id)
                update_product_boms()
                product_ids.clear()

            bom = product_boms.get(resolved_product)
            if bom:
                converted_line_quantity = (
                    current_line.product_uom_id._compute_quantity(
                        line_quantity / bom.product_qty, bom.product_uom_id
                    )
                )
                bom_lines += [
                    (
                        line,
                        resolved_product,
                        converted_line_quantity,
                        current_line,
                    )
                    for line in bom.bom_line_ids
                ]
                for bom_line in bom.bom_line_ids:
                    if not bom_line.product_id:
                        continue
                    graph[resolved_product.product_tmpl_id.id].append(
                        bom_line.product_id.product_tmpl_id.id
                    )
                    if bom_line.product_id.product_tmpl_id.id in V and check_cycle(
                        bom_line.product_id.product_tmpl_id.id,
                        {key: False for key in V},
                        {key: False for key in V},
                        graph,
                    ):
                        raise UserError(
                            _(
                                "Recursion error!  A product with a Bill of Material "
                                "should not have itself in its BoM or child BoMs!"
                            )
                        )
                    V |= {bom_line.product_id.product_tmpl_id.id}
                    if bom_line.product_id not in product_boms:
                        product_ids.add(bom_line.product_id.id)
                boms_done.append(
                    (
                        bom,
                        {
                            "qty": converted_line_quantity,
                            "product": current_product,
                            "original_qty": quantity,
                            "parent_line": current_line,
                        },
                    )
                )
            else:
                rounding = current_line.product_uom_id.rounding
                line_quantity = float_round(
                    line_quantity,
                    precision_rounding=rounding,
                    rounding_method="UP",
                )
                virtual_line = current_line.new(origin=current_line)
                virtual_line.product_id = resolved_product
                lines_done.append(
                    (
                        virtual_line,
                        {
                            "qty": line_quantity,
                            "product": current_product,
                            "original_qty": quantity,
                            "parent_line": parent_line,
                        },
                    )
                )

        return boms_done, lines_done
