import re
import logging
import uuid
import unicodedata
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_compare
from dateutil.relativedelta import relativedelta

_logger = logging.getLogger(__name__)

class MrpProductionGroupAddWizard(models.TransientModel):
    _name = "mrp.production.group.add.wizard"
    _description = "Filtro / Añadir OF a agrupación"

    group_id = fields.Many2one("mrp.production.group")

    wizard_key = fields.Char(
        index=True,
        required=True,
        readonly=True,
        default=lambda self: uuid.uuid4().hex,
    )

    picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo de operación",
        required=False,
        domain=[("code", "=", "mrp_operation")],
    )

    planned_start_from = fields.Date(
        string="Fecha prevista desde"
    )
    planned_start_to = fields.Date(
        string="Fecha prevista hasta"
    )
    
    attribute_type_ids = fields.Many2many(
        "product.attribute.type",
        string="Tipos de atributo",
        relation="mrp_pg_addw_attrtype_rel",
        column1="wizard_id",
        column2="type_id",
    )

    attribute_value_ids = fields.Many2many(
        "mrp.production.group.attribute.value.name",
        string="Valores del atributo",
        relation="mrp_pg_addw_valname_rel",
        column1="wizard_id",
        column2="valname_id",
    )

    workcenter_ids = fields.Many2many(
        "mrp.workcenter",
        string="Primer centro de producción",
        relation="mrp_pg_addw_wc_rel",
        column1="wizard_id",
        column2="workcenter_id",
    )
    #medidas
    length_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_len_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Largo",
    )
    height_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_hgt_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Alto",
    )
    width_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_wdt_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Ancho/Grosor",
    )

    available_length_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_av_len_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Largos disponibles",
        readonly=True,
    )
    available_height_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_av_hgt_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Altos disponibles",
        readonly=True,
    )
    available_width_value_ids = fields.Many2many(
        comodel_name="mrp.production.group.measure.value",
        relation="mpg_wiz_av_wdt_val_rel",
        column1="wizard_id",
        column2="measure_id",
        string="Anchos disponibles",
        readonly=True,
    )

    product_id = fields.Many2many(
        comodel_name="product.product",
        relation="mpg_wiz_saleprod_rel",
        column1="wizard_id",
        column2="product_id",
        string="Producto de venta",
    )

    code_prefix_ids = fields.Many2many(
        comodel_name="mrp.production.group.code_prefix",
        relation="mpg_wiz_codeprefix_rel",
        column1="wizard_id",
        column2="code_prefix_id",
        string="Prefijo",
    )
    code_prefix_search = fields.Char(
        string="Code prefix",
        help="Filtro tipo buscador. Puedes poner varios tokens separados por espacios/comas. Ej: 'M_S ST' (OR).",
    )
    code_prefix_search_2 = fields.Char(string="Code prefix (2)")
    code_prefix_search_3 = fields.Char(string="Code prefix (3)")
    code_prefix_search_4 = fields.Char(string="Code prefix (4)")


    sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="mpg_wiz_sale_rel",
        column1="wizard_id",
        column2="sale_id",
        string="Pedido(s) de venta origen",
    )

    model_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="mpg_wiz_modelprod_rel",
        column1="wizard_id",
        column2="product_id",
        string="Código Modelo",
    )

    exclude_grouped = fields.Boolean(
        string="Excluir OF ya agrupadas", 
        default=True
    )

    mo_ids = fields.Many2many(
        "mrp.production", 
        string="Órdenes candidatas"
    )
    warning_msg = fields.Text(
        readonly=True
    )

    available_attribute_type_ids = fields.Many2many(
        "product.attribute.type",
        # compute="_compute_available_network",
        readonly=True,
        relation="mrp_pg_addw_av_attrtype_rel",
        column1="wizard_id",
        column2="type_id",
    )

    available_attribute_value_ids = fields.Many2many(
        "mrp.production.group.attribute.value.name",
        string="Valores disponibles",
        relation="mrp_pg_addw_av_val_rel",
        column1="wizard_id",
        column2="valname_id",
        # compute="_compute_available_network",
        readonly=True,
    )

    available_workcenter_ids = fields.Many2many(
        "mrp.workcenter",
        # compute="_compute_available_network",
        string="Centros disponibles",
        readonly=True,
        relation="mrp_pg_addw_av_wc_rel",
        column1="wizard_id",
        column2="workcenter_id",
    )

    available_code_prefix_ids = fields.Many2many(
        comodel_name="mrp.production.group.code_prefix",
        relation="mpg_wiz_av_codeprefix_rel",
        column1="wizard_id",
        column2="code_prefix_id",
        # compute="_compute_available_network",
        string="Prefijos disponibles",
        readonly=True,
    )

    available_sale_order_ids = fields.Many2many(
        comodel_name="sale.order",
        relation="mpg_wiz_av_sale_rel",
        column1="wizard_id",
        column2="sale_id",
        # compute="_compute_available_network",
        string="Pedidos de venta disponibles",
        readonly=True,
    )

    available_model_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="mpg_wiz_av_modelprod_rel",
        column1="wizard_id",
        column2="product_id",
        # compute="_compute_available_network",
        string="Modelos disponibles",
        readonly=True,
    )
    
    mo_ids = fields.Many2many("mrp.production", string="Órdenes candidatas")
    mo_count = fields.Integer(
        string="Órdenes a buscar",
        compute="_compute_preview_stats",
        readonly=True,
    )
    total_product_qty = fields.Float(
        string="Total piezas",
        compute="_compute_preview_stats",
        readonly=True,
    )
    
    
    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        ctx = dict(self.env.context or {})

        pt_id = (
            ctx.get("default_picking_type_id")
            or ctx.get("picking_type_id")
            or ctx.get("search_default_picking_type_id")
        )

        # Si venimos desde una agrupación, intentamos inferir STP1 desde sus OFs
        if not pt_id:
            group_id = res.get("group_id") or ctx.get("default_group_id")
            if group_id:
                group = self.env["mrp.production.group"].browse(group_id).exists()
                if group:
                    mos = group.production_ids
                    pts = mos.mapped("picking_type_id").exists()
                    if len(pts) == 1:
                        pt_id = pts.id

        # Si venimos desde un picking type abierto (acción contextual)
        if not pt_id and ctx.get("active_model") == "stock.picking.type":
            pt = self.env["stock.picking.type"].browse(ctx.get("active_id")).exists()
            if pt and pt.code == "mrp_operation":
                pt_id = pt.id

        if pt_id and "picking_type_id" in fields_list:
            res["picking_type_id"] = pt_id

        if "wizard_key" in fields_list and not res.get("wizard_key"):
            res["wizard_key"] = uuid.uuid4().hex

        return res


    def _ensure_wizard_key(self):
        for w in self:
            if not w.wizard_key:
                w.wizard_key = uuid.uuid4().hex


    def _get_company_id(self):
        self.ensure_one()
        if self.group_id:
            return self.group_id.company_id.id
        return self.env.company.id


    def _has_component_filters(self):
        self.ensure_one()
        return bool(
            self.attribute_type_ids
            or self.attribute_value_ids
            or self.length_value_ids
            or self.height_value_ids
            or self.width_value_ids
        )


    def _has_any_extra_filters(self):
        self.ensure_one()
        return bool(self._has_component_filters() or self.workcenter_ids)


    def _attribute_type_field_name(self):
        Attr = self.env["product.attribute"]
        preferred = ["attribute_type_id", "type_id", "product_attribute_type_id"]
        for fname in preferred:
            f = Attr._fields.get(fname)
            if f and getattr(f, "comodel_name", None) == "product.attribute.type":
                return fname
        for fname, f in Attr._fields.items():
            if getattr(f, "comodel_name", None) == "product.attribute.type":
                return fname
        return False


    def _check_measure_fields_available(self):
        self.ensure_one()
        if not (self.length_value_ids or self.height_value_ids or self.width_value_ids):
            return

        PP = self.env["product.product"]
        missing = [f for f in ("product_length", "product_height", "product_width") if f not in PP._fields]
        if missing:
            raise UserError(
                _("Los filtros de medidas no están disponibles porque faltan campos en product.product: %s")
                % ", ".join(missing)
            )


    def _sanitize_mo_ids_commands(self, commands):
        if not commands:
            return commands

        ids = []
        for cmd in commands:
            if not cmd:
                continue
            op = cmd[0]

            if op == 6:
                return [(6, 0, cmd[2] or [])]

            if op == 4:
                ids.append(cmd[1])
            elif op == 1:
                ids.append(cmd[1])
            elif op == 5:
                ids = []
            elif op == 3:
                try:
                    ids.remove(cmd[1])
                except ValueError:
                    pass

        if not ids:
            return [(5, 0, 0)]
        return [(6, 0, list(dict.fromkeys(ids)))]

    
    def _or_domain_terms(self, terms):
        terms = [t for t in (terms or []) if t and t[2]]
        if not terms:
            return []
        dom = [terms[0]]
        for t in terms[1:]:
            dom = ["|"] + dom + [t]
        return dom


    def _sale_names_from_origin_strings(self, origins):
        out = []
        for o in origins or []:
            if not o:
                continue
            for part in o.replace(";", ",").split(","):
                part = (part or "").strip()
                if not part:
                    continue
                token = part.split()[0].strip().rstrip(":-")
                if token:
                    out.append(token)
        return list(dict.fromkeys(out))


    def _or_domain(self, field_name, operator, values):
        values = [v for v in (values or []) if v]
        if not values:
            return []
        dom = [(field_name, operator, values[0])]
        for v in values[1:]:
            dom = ["|"] + dom + [(field_name, operator, v)]
        return dom


    def _norm_value_name(self, s):
        s = s or ""
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("\u00A0", " ")
        s = s.replace("\u200B", "")
        s = s.replace("\u2060", "")
        s = s.replace("×", "x")
        s = re.sub(r"\s+", " ", s).strip()
        return s


    @api.depends("mo_ids", "mo_ids.product_qty")
    def _compute_preview_stats(self):
        for w in self:
            mos = w.mo_ids
            w.mo_count = len(mos)
            w.total_product_qty = sum(mos.mapped("product_qty")) if mos else 0.0

    
    def _dedup_value_names(self, names):
        seen = set()
        out = []
        for n in names or []:
            n2 = self._norm_value_name(n)
            if not n2:
                continue
            k = n2.casefold()
            if k in seen:
                continue
            seen.add(k)
            out.append(n2)
        return out


    def _sync_attr_value_name_records(self, names):
        self.ensure_one()
        self._ensure_wizard_key()

        names = [self._norm_value_name(n) for n in (names or [])]
        names = self._dedup_value_names(names)
        if not names:
            return self.env["mrp.production.group.attribute.value.name"].browse()

        Model = self.env["mrp.production.group.attribute.value.name"].sudo()
        key = self.wizard_key

        wanted = {self._norm_value_name(n).casefold(): self._norm_value_name(n) for n in names}

        existing = Model.search([("wizard_key", "=", key), ("name_key", "in", list(wanted.keys()))])
        by_key = {r.name_key: r for r in existing}

        to_create = []
        for k2, canon in wanted.items():
            if k2 not in by_key:
                to_create.append({"wizard_key": key, "name": canon})

        if to_create:
            created = Model.create(to_create)
            for r in created:
                by_key[r.name_key] = r

        ids = []
        for k2, canon in wanted.items():
            r = by_key.get(k2)
            if r and r.id not in ids:
                if r.name != canon:
                    r.name = canon
                ids.append(r.id)

        return Model.browse(ids)


    def _cleanup_network_selections(self):
        self.ensure_one()

        if self.attribute_type_ids and self.available_attribute_type_ids:
            self.attribute_type_ids = [(6, 0, (self.attribute_type_ids & self.available_attribute_type_ids).ids)]

        if self.attribute_value_ids and self.available_attribute_value_ids:
            self.attribute_value_ids = [(6, 0, (self.attribute_value_ids & self.available_attribute_value_ids).ids)]

        if self.workcenter_ids and self.available_workcenter_ids:
            self.workcenter_ids = [(6, 0, (self.workcenter_ids & self.available_workcenter_ids).ids)]

        if self.code_prefix_ids and self.available_code_prefix_ids:
            self.code_prefix_ids = [(6, 0, (self.code_prefix_ids & self.available_code_prefix_ids).ids)]

        if self.model_product_ids and self.available_model_product_ids:
            self.model_product_ids = [(6, 0, (self.model_product_ids & self.available_model_product_ids).ids)]

        if self.sale_order_ids and self.available_sale_order_ids:
            self.sale_order_ids = [(6, 0, (self.sale_order_ids & self.available_sale_order_ids).ids)]


    def _product_attributes_present(self, product):
        Attr = self.env["product.attribute"]
        attrs = Attr.browse()

        if "product_template_variant_value_ids" in product._fields:
            attrs |= product.product_template_variant_value_ids.mapped("attribute_id")

        if "product_template_attribute_value_ids" in product._fields:
            attrs |= product.product_template_attribute_value_ids.mapped("attribute_id")

        attrs |= product.product_tmpl_id.attribute_line_ids.mapped("attribute_id")
        return attrs.exists()


    def _mo_component_products(self, mo):
        moves = mo.move_raw_ids.filtered(lambda m: m.state != "cancel" and m.product_id)
        prods = moves.mapped("product_id")
        if prods:
            return prods
        if mo.bom_id:
            return mo.bom_id.bom_line_ids.mapped("product_id")
        return self.env["product.product"].browse()


    def _product_values_for_attr(self, product, attr):
        tmpl = product.product_tmpl_id
        vals = self.env["product.attribute.value"].browse()

        if "product_template_variant_value_ids" in product._fields:
            vals |= product.product_template_variant_value_ids.filtered(
                lambda r: r.attribute_id == attr
            ).mapped("product_attribute_value_id")

        if not vals and "product_template_attribute_value_ids" in product._fields:
            vals |= product.product_template_attribute_value_ids.filtered(
                lambda r: r.attribute_id == attr
            ).mapped("product_attribute_value_id")

        if (not vals) and self.env.context.get("pmx_wizard_allow_template_attr_values"):
            line = tmpl.attribute_line_ids.filtered(lambda l: l.attribute_id == attr)
            if line:
                vals |= line.mapped("value_ids")

        return vals


    def _product_matches_component_filters(self, product):
        self.ensure_one()
        if not self._has_component_filters():
            return True

        attrs_present = self._product_attributes_present(product)
        fname = self._attribute_type_field_name()
        Attr = self.env["product.attribute"]

        if self.attribute_type_ids and fname:
            want_type_ids = set(self.attribute_type_ids.ids)
            present_type_ids = set()
            fdef = Attr._fields.get(fname)

            for attr in attrs_present:
                v = attr[fname]
                if fdef and fdef.type == "many2one":
                    if v:
                        present_type_ids.add(v.id)
                elif fdef and fdef.type == "many2many":
                    present_type_ids |= set(v.ids)

            if not want_type_ids.issubset(present_type_ids):
                return False

        selected_names = self._dedup_value_names(self.attribute_value_ids.mapped("name"))
        if selected_names:
            attrs_for_values = attrs_present
            if self.attribute_type_ids and fname:
                want_type_ids = set(self.attribute_type_ids.ids)
                fdef = Attr._fields.get(fname)

                def _attr_in_types(a):
                    v = a[fname]
                    if fdef and fdef.type == "many2one":
                        return bool(v and v.id in want_type_ids)
                    if fdef and fdef.type == "many2many":
                        return bool(set(v.ids) & want_type_ids)
                    return True

                attrs_for_values = attrs_present.filtered(_attr_in_types)

            present_names = []
            for attr in attrs_for_values:
                for val in self._product_values_for_attr(product, attr):
                    if val.name:
                        present_names.append(val.name)

            present_cf = [(n or "").casefold() for n in present_names]
            wanted_cf = [(w or "").strip().casefold() for w in selected_names if w and w.strip()]
            if wanted_cf and not any(any(w in p for p in present_cf) for w in wanted_cf):    
                return False

        PP = self.env["product.product"]
        if self.length_value_ids and "product_length" in PP._fields:
            wanted = set(self.length_value_ids.filtered(lambda r: r.kind == "length").mapped("value_float"))
            pv = product.product_length or 0.0
            if wanted and not any(float_compare(pv, x, precision_digits=2) == 0 for x in wanted):
                return False

        if self.height_value_ids and "product_height" in PP._fields:
            wanted = set(self.height_value_ids.filtered(lambda r: r.kind == "height").mapped("value_float"))
            pv = product.product_height or 0.0
            if wanted and not any(float_compare(pv, x, precision_digits=2) == 0 for x in wanted):
                return False

        if self.width_value_ids and "product_width" in PP._fields:
            wanted = set(self.width_value_ids.filtered(lambda r: r.kind == "width").mapped("value_float"))
            pv = product.product_width or 0.0
            if wanted and not any(float_compare(pv, x, precision_digits=2) == 0 for x in wanted):
                return False

        return True

    
    def action_search_attribute_values(self):
        return self.action_search()


    def _mo_products_to_check(self, mo):
        self.ensure_one()
        return (mo.product_id | self._mo_component_products(mo)).exists()


    def _filter_mos_by_components(self, mos):
        self.ensure_one()
        if not self._has_component_filters():
            return mos

        self._check_measure_fields_available()

        def mo_ok(mo):
            for p in self._mo_products_to_check(mo):
                if self._product_matches_component_filters(p):
                    return True
            return False

        return mos.filtered(mo_ok)


    def _mo_workcenters(self, mo):
        WC = self.env["mrp.workcenter"].browse()

        if "workorder_ids" in mo._fields:
            wcs = mo.workorder_ids.mapped("workcenter_id")
            if wcs:
                return wcs

        if mo.bom_id and "operation_ids" in mo.bom_id._fields:
            wcs = mo.bom_id.operation_ids.mapped("workcenter_id")
            if wcs:
                return wcs

        return WC


    def _first_workcenter_id(self, mo):
        wo = mo.workorder_ids.sorted(key=lambda w: (w._sequence, w.id))[:1]
        if wo:
            return wo.workcenter_id.id
        return False


    def _mo_workcenters_prefix_ids(self, mo, depth):
        depth = int(depth or 0)
        if depth <= 0:
            return []

        if "workorder_ids" in mo._fields and mo.workorder_ids:
            wos = mo.workorder_ids.sorted(key=lambda w: (w._sequence, w.id))[:depth]
            return wos.mapped("workcenter_id").ids

        if mo.bom_id and "operation_ids" in mo.bom_id._fields and mo.bom_id.operation_ids:
            ops = mo.bom_id.operation_ids.sorted(key=lambda o: (o._sequence, o.id))[:depth]
            return ops.mapped("workcenter_id").ids

        return []


    def _filter_mos_by_workcenters(self, mos):
        self.ensure_one()
        if not self.workcenter_ids:
            return mos

        wanted = set(self.workcenter_ids.ids)
        depth = len(wanted)

        def mo_ok(mo):
            prefix_wc_ids = set(self._mo_workcenters_prefix_ids(mo, depth))
            return bool(prefix_wc_ids & wanted)

        return mos.filtered(mo_ok)


    def _base_domain(self):
        self.ensure_one()

        dom = [
            ("state", "not in", ("done", "cancel", "progress")),
            ("company_id", "=", self._get_company_id()),
        ]

        if self.exclude_grouped:
            dom.append(("group_id", "=", False))
        pt = self.picking_type_id or (self.group_id.picking_type_id if self.group_id else False)

        if pt:
            dom.append(("picking_type_id", "=", pt.id))
        elif self.env.context.get("active_model") == "stock.picking.type":
            dom.append(("picking_type_id.code", "=", "mrp_operation"))

        if self.planned_start_from:
            dom.append(("date_planned_start", ">=", fields.Datetime.to_datetime(self.planned_start_from)))
        if self.planned_start_to:
            dt_to = fields.Datetime.to_datetime(self.planned_start_to) + relativedelta(days=1)
            dom.append(("date_planned_start", "<", dt_to))

        if self.product_id:
            MO = self.env["mrp.production"]
            if "sale_line_id" in MO._fields:
                dom.append(("sale_line_id.product_id", "in", self.product_id.ids))
            else:
                dom.append(("product_id", "in", self.product_id.ids))

        if self.model_product_ids:
            dom.append(("product_id", "in", self.model_product_ids.ids))
            
        # if self.workcenter_ids:
        #     MO = self.env["mrp.production"]
        #     terms = []
        #     if "workorder_ids" in MO._fields:
        #         terms.append(("workorder_ids.workcenter_id", "in", self.workcenter_ids.ids))
        #     if "bom_id" in MO._fields and "operation_ids" in self.env["mrp.bom"]._fields:
        #         terms.append(("bom_id.operation_ids.workcenter_id", "in", self.workcenter_ids.ids))
        #     dom += self._or_domain_terms(terms)

        if self.sale_order_ids:
            MO = self.env["mrp.production"]
            names = [n for n in self.sale_order_ids.mapped("name") if n]

            terms = []
            for n in names:
                if "origin" in MO._fields:
                    terms.append(("origin", "ilike", n))
                if "procurement_group_id" in MO._fields:
                    terms.append(("procurement_group_id.name", "ilike", n))
                if "sale_line_id" in MO._fields:
                    terms.append(("sale_line_id.order_id.name", "ilike", n))

            dom += self._or_domain_terms(terms)
            
        if self.code_prefix_search or self.code_prefix_search_2 or self.code_prefix_search_3 or self.code_prefix_search_4:
            MO = self.env["mrp.production"]
            PT = self.env["product.template"]
            if "code_prefix" not in PT._fields:
                raise UserError(_("El campo code_prefix no existe en product.template, pero el wizard lo está filtrando."))

            raws = [
                (self.code_prefix_search or "").strip(),
                (self.code_prefix_search_2 or "").strip(),
                (self.code_prefix_search_3 or "").strip(),
                (self.code_prefix_search_4 or "").strip(),
            ]
            tokens = []
            for raw in raws:
                if not raw:
                    continue
                tokens.extend([t for t in re.split(r"[,\s;]+", raw) if t])

            if tokens:
                f_cp = PT._fields["code_prefix"]
                if f_cp.type == "many2one":
                    paths = ["product_id.product_tmpl_id.code_prefix.name"]
                    if "sale_line_id" in MO._fields:
                        paths.append("sale_line_id.product_id.product_tmpl_id.code_prefix.name")
                else:
                    paths = ["product_id.product_tmpl_id.code_prefix"]
                    if "sale_line_id" in MO._fields:
                        paths.append("sale_line_id.product_id.product_tmpl_id.code_prefix")

                terms = []
                for p in paths:
                    for t in tokens:
                        terms.append((p, "ilike", t))

                dom += self._or_domain_terms(terms)
 

        if self.code_prefix_ids:
            MO = self.env["mrp.production"]
            PT = self.env["product.template"]
            if "code_prefix" not in PT._fields:
                raise UserError(_("El campo code_prefix no existe en product.template, pero el wizard lo está filtrando."))

            prefixes = [p for p in self.code_prefix_ids.mapped("name") if p]
            if prefixes:
                f_cp = PT._fields["code_prefix"]
                terms = []
                
                if f_cp.type == "many2one":
                    terms.append(("product_id.product_tmpl_id.code_prefix.name", "in", prefixes))
                    if "sale_line_id" in MO._fields:
                        terms.append(("sale_line_id.product_id.product_tmpl_id.code_prefix.name", "in", prefixes))
                else:
                    terms.append(("product_id.product_tmpl_id.code_prefix.name", "in", prefixes))
                    if "sale_line_id" in MO._fields:
                        terms.append(("sale_line_id.product_id.product_tmpl_id.code_prefix", "in", prefixes))
                
                dom += self._or_domain_terms(terms)
                        
        return dom


    #@api.depends("mo_ids", "group_id", "attribute_type_ids", "attribute_value_ids")
    def _compute_available_network(self):
        Attr = self.env["product.attribute"]
        Val = self.env["product.attribute.value"]
        Type = self.env["product.attribute.type"]
        WC = self.env["mrp.workcenter"]
        Sale = self.env["sale.order"]
        PT = self.env["product.template"]
        PrefixModel = self.env["mrp.production.group.code_prefix"].sudo()
        ValName = self.env["mrp.production.group.attribute.value.name"].sudo()
        Prod = self.env["product.product"]
        Measure = self.env["mrp.production.group.measure.value"].sudo()


        for w in self:
            w._ensure_wizard_key()

            w.available_attribute_type_ids = Type.browse()
            w.available_attribute_value_ids = ValName.browse()
            w.available_workcenter_ids = WC.browse()
            w.available_sale_order_ids = Sale.browse()
            w.available_model_product_ids = Prod.browse()
            w.available_code_prefix_ids = PrefixModel.browse()
            
            w.available_length_value_ids = Measure.browse()
            w.available_height_value_ids = Measure.browse()
            w.available_width_value_ids = Measure.browse()

            mos = w.mo_ids
            if not mos:
                continue

            try:
                fname = w._attribute_type_field_name()
                f_type = Attr._fields.get(fname) if fname else None

                all_products = Prod.browse()
                all_workcenters = WC.browse()

                for mo in mos:
                    all_products |= w._mo_products_to_check(mo)
                    all_workcenters |= w._mo_workcenters(mo)

                all_products = all_products.exists()
                
                Measure = self.env["mrp.production.group.measure.value"].sudo()
                def _sync_measures(kind, values):
                    key = w.wizard_key  # usa el wizard del bucle

                    wanted = []
                    seen = set()
                    for v in values or []:
                        if v is None:
                            continue
                        canon = round(float(v), 2)
                        if canon in seen:
                            continue
                        seen.add(canon)
                        wanted.append(canon)

                    if not wanted:
                        Measure.search([("wizard_key", "=", key), ("kind", "=", kind)]).unlink()
                        return Measure.browse()

                    existing = Measure.search([("wizard_key", "=", key), ("kind", "=", kind)])
                    by_val = {round(r.value_float or 0.0, 2): r for r in existing if r.value_float is not None}

                    to_create = []
                    for canon in wanted:
                        if canon not in by_val:
                            to_create.append({
                                "wizard_key": key,
                                "kind": kind,
                                "value_float": canon,
                                "name": str(canon),
                            })

                    created = Measure.create(to_create) if to_create else Measure.browse()
                    for r in created:
                        by_val[round(r.value_float or 0.0, 2)] = r

                    wanted_set = set(wanted)
                    to_unlink = existing.filtered(lambda r: round(r.value_float or 0.0, 2) not in wanted_set)
                    if to_unlink:
                        to_unlink.unlink()

                    return Measure.browse([by_val[v].id for v in wanted if v in by_val])


                PP = self.env["product.product"]
                if all_products:
                    if "product_length" in PP._fields:
                        _sync_measures("length", all_products.mapped("product_length"))
                    if "product_height" in PP._fields:
                        _sync_measures("height", all_products.mapped("product_height"))
                    if "product_width" in PP._fields:
                        _sync_measures("width", all_products.mapped("product_width"))

                
                all_workcenters = all_workcenters.exists()

                attrs = Attr.browse()
                vals = Val.browse()

                if all_products:
                    if "product_template_variant_value_ids" in all_products._fields:
                        ptvv = all_products.mapped("product_template_variant_value_ids")
                        vals |= ptvv.mapped("product_attribute_value_id")
                        attrs |= ptvv.mapped("attribute_id")

                    if "product_template_attribute_value_ids" in all_products._fields:
                        ptav = all_products.mapped("product_template_attribute_value_ids")
                        vals |= ptav.mapped("product_attribute_value_id")
                        attrs |= ptav.mapped("attribute_id")

                    tmpls = all_products.mapped("product_tmpl_id")
                    attrs |= tmpls.mapped("attribute_line_ids").mapped("attribute_id")
                    # vals |= tmpls.mapped("attribute_line_ids").mapped("value_ids")

                attrs = attrs.exists()
                vals = vals.exists()

                if fname and attrs:
                    types_base = attrs.mapped(fname).exists()
                else:
                    types_base = Type.search([])

                attrs_domain = attrs
                if fname and w.attribute_type_ids and attrs_domain:
                    wanted_type_ids = set(w.attribute_type_ids.ids)
                    if f_type and f_type.type == "many2one":
                        attrs_domain = attrs_domain.filtered(lambda a: a[fname] and a[fname].id in wanted_type_ids)
                    elif f_type and f_type.type == "many2many":
                        attrs_domain = attrs_domain.filtered(lambda a: bool(set(a[fname].ids) & wanted_type_ids))
                    else:
                        pass

                selected_names = w._dedup_value_names(w.attribute_value_ids.mapped("name"))
                if selected_names and attrs_domain:
                    sel_cf = [n.casefold() for n in selected_names]

                    def _match_val(v):
                        vn = (v.name or "").casefold()
                        return any(s in vn for s in sel_cf)

                    allowed_attr_ids = set(attrs_domain.ids)
                    matching_vals = vals.filtered(
                        lambda v: v.attribute_id and v.attribute_id.id in allowed_attr_ids and _match_val(v)
                    )
                    attrs_domain = matching_vals.mapped("attribute_id").exists()

                if attrs_domain:
                    allowed_attr_ids = set(attrs_domain.ids)
                    vals_domain = vals.filtered(lambda v: v.attribute_id and v.attribute_id.id in allowed_attr_ids)
                else:
                    vals_domain = Val.browse()

                if fname and attrs_domain:
                    types_domain = attrs_domain.mapped(fname).exists()
                else:
                    types_domain = types_base

                w.available_attribute_type_ids = types_domain

                val_names = w._dedup_value_names(vals_domain.mapped("name"))
                w.available_attribute_value_ids = w._sync_attr_value_name_records(val_names)

                w.available_workcenter_ids = all_workcenters

                products_from_mo = mos.mapped("product_id").exists()
                w.available_model_product_ids = products_from_mo
                
                products_from_sale = Prod.browse()
                if "sale_line_id" in mos._fields:
                    products_from_sale |= mos.mapped("sale_line_id.product_id").exists()


                company_id = w.group_id.company_id.id if w.group_id else w.env.company.id

                sale_orders = Sale.browse()

                if "sale_line_id" in mos._fields:
                    sale_orders |= mos.mapped("sale_line_id.order_id").exists()

                tokens = w._sale_names_from_origin_strings(mos.mapped("origin"))

                if "procurement_group_id" in mos._fields:
                    tokens += [n for n in mos.mapped("procurement_group_id.name") if n]
                tokens = list(dict.fromkeys(tokens))

                if tokens:
                    sale_orders |= Sale.search([
                        ("company_id", "=", company_id),
                        ("name", "in", tokens),
                    ])

                if not sale_orders and tokens:
                    sale_orders = Sale.search(
                        [("company_id", "=", company_id)] + w._or_domain("name", "ilike", tokens[:50])
                    )

                w.available_sale_order_ids = sale_orders.exists()


                tmpls_for_prefix = (products_from_mo | products_from_sale).mapped("product_tmpl_id").exists()


                prefix_values = []
                if tmpls_for_prefix and "code_prefix" in PT._fields:
                    f_cp = PT._fields["code_prefix"]
                    if f_cp.type == "many2one":
                        cp_recs = tmpls_for_prefix.mapped("code_prefix").exists()                        
                        if cp_recs:
                            if "name" in cp_recs._fields:
                                prefix_values = [p for p in cp_recs.mapped("name") if p]
                            else:
                                prefix_values = [p for p in cp_recs.mapped("display_name") if p]
                    else:
                        prefix_values = [p for p in tmpls_for_prefix.mapped("code_prefix") if p]

                prefix_values = list(dict.fromkeys(prefix_values))

                prefix_recs = PrefixModel.browse()
                if prefix_values:
                    prefix_recs = PrefixModel.search([
                        ("company_id", "=", company_id),
                        ("name", "in", prefix_values),
                    ])

                w.available_code_prefix_ids = prefix_recs

            except Exception as e:
                _logger.exception("Error calculando available_* en wizard_key=%s", w.wizard_key)
                raise 


    def _recompute_candidates_and_domains(self):
        self.ensure_one()

        dom = self._base_domain()

        limit = int(self.env["ir.config_parameter"].sudo().get_param(
            "pmx_mrp_production_group_yostesis.filter_wizard_limit", "300"
        ))

        MO = self.env["mrp.production"]
        order = "date_planned_start asc, id asc"

        has_components = self._has_component_filters()
        has_wc = bool(self.workcenter_ids)

        if (not has_components) and (not has_wc):
            mos = MO.search(dom, order=order, limit=limit + 1)
            truncated = len(mos) > limit
            mos = mos[:limit]
            self.mo_ids = [(6, 0, mos.ids)]
            self.warning_msg = truncated and _(
                "Se han encontrado más de %(limit)s resultados. Se muestran solo los primeros %(limit)s. "
                "Refina filtros para acotar más."
            ) % {"limit": limit} or False
            return

        batch = 200
        offset = 0
        picked_ids = []
        seen = set()
        scanned = 0
        max_scan = int(self.env["ir.config_parameter"].sudo().get_param(
            "pmx_mrp_production_group_yostesis.filter_wizard_max_scan", str(limit * 20)
        ))

        while len(picked_ids) <= limit and scanned < max_scan:
            chunk = MO.search(dom, order=order, offset=offset, limit=batch)
            if not chunk:
                break
            offset += batch
            scanned += len(chunk)

            if has_components:
                chunk = self._filter_mos_by_components(chunk)
            if has_wc:
                chunk = self._filter_mos_by_workcenters(chunk)

            for mo in chunk:
                if mo.id in seen:
                    continue
                seen.add(mo.id)
                picked_ids.append(mo.id)
                if len(picked_ids) > limit:
                    break

        truncated = len(picked_ids) > limit
        if truncated:
            picked_ids = picked_ids[:limit]

        self.mo_ids = [(6, 0, picked_ids)]
        if truncated:
            self.warning_msg = _(
                "Se han encontrado más de %(limit)s resultados. Se muestran solo los primeros %(limit)s. "
                "Refina filtros para acotar más."
            ) % {"limit": limit}
        elif scanned >= max_scan:
            self.warning_msg = _(
                "Se han inspeccionado %(max_scan)s OF sin completar el límite de resultados. "
                "Refina filtros para acotar más."
            ) % {"max_scan": max_scan}
        else:
            self.warning_msg = False


    @api.onchange(
        "picking_type_id",
        "planned_start_from",
        "planned_start_to",
        "attribute_type_ids",
        "attribute_value_ids",
        "workcenter_ids",
        "length",
        "height",
        "width",
        "product_id",
        "model_product_ids",
        "sale_order_ids",
        "code_prefix_ids",
        "code_prefix_search",
        "code_prefix_search_2",
        "code_prefix_search_3",
        "code_prefix_search_4",
        "exclude_grouped",
    )
    def _onchange_any_filter(self):
        for w in self:
            w._ensure_wizard_key()
            # w._recompute_candidates_and_domains()
            # w._compute_available_network()
            # w._cleanup_network_selections()
            w.warning_msg = _("Filtros cambiados. Pulsa 'Buscar' para recalcular.")
            w.mo_ids = [(5, 0, 0)]


    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if "wizard_key" not in vals or not vals.get("wizard_key"):
                vals["wizard_key"] = uuid.uuid4().hex
            if "mo_ids" in vals:
                vals["mo_ids"] = self._sanitize_mo_ids_commands(vals["mo_ids"])
        records = super().create(vals_list)
        for w in records:
            w._recompute_candidates_and_domains()
            # w._compute_available_network()
            # w._cleanup_network_selections()
        return records


    def action_search(self):
        self.ensure_one()
        # if not self.picking_type_id:
        #     raise UserError(_("Debes seleccionar un Tipo de operación."))
        self._recompute_candidates_and_domains()
        self._compute_available_network()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production.group.add.wizard",
            "view_mode": "form",
            "res_id": self.id,
            "target": "new",
        }


    def action_apply_filter(self):
        self.ensure_one()

        self._recompute_candidates_and_domains()
        mo_ids = self.mo_ids.ids

        stp1 = self.picking_type_id
        stp3 = False
        if stp1:
            # STP1 -> STP3
            if stp1.code == "mrp_operation":
                stp3 = stp1.pmx_mrp_group_target_picking_type_id
                if not stp3:
                    raise UserError(_(
                        "El Tipo de operación '%s' no tiene configurado "
                        "'Tipo operación para la Agrupación OFs' (STP3)."
                    ) % stp1.display_name)
            else:
                stp3 = stp1

        ctx = dict(self.env.context or {})
        ctx.update({
            "preselect_ids": mo_ids,
            "preselect_model": "mrp.production",
        })

        if stp1:
            ctx["pmx_mrp_group_stp1_id"] = stp1.id
        if stp3:
            ctx["pmx_mrp_group_target_picking_type_id"] = stp3.id
            ctx["default_picking_type_id"] = stp3.id  # <-- clave

        return {
            "type": "ir.actions.act_window",
            "name": _("Órdenes de fabricación (filtradas)"),
            "res_model": "mrp.production",
            "view_mode": "tree,form",
            "target": "current",
            "domain": [("id", "in", mo_ids)],
            "context": ctx,
        }


    def action_add(self):
        self.ensure_one()
        stp1 = self.picking_type_id
        if not stp1:
            raise UserError(_("Debes seleccionar un Tipo de operación."))

        stp3 = stp1
        if stp1.code == "mrp_operation":
            stp3 = stp1.pmx_mrp_group_target_picking_type_id
            if not stp3:
                raise UserError(_(
                    "El Tipo de operación '%s' no tiene configurado 'Tipo operación para Agrupación OFs' (STP3)."
                ) % stp1.display_name)

        group = self.group_id
        created = False
        if not group:
            group = self.env["mrp.production.group"].create({
                "company_id": self.env.company.id,
                "picking_type_id": stp3.id,
            })
            self.group_id = group.id
            created = True
        else:
            if group.picking_type_id and group.picking_type_id != stp3:
                raise UserError(_(
                    "El Tipo de operación de la agrupación es '%s' y no coincide con el configurado ('%s') para '%s'."
                ) % (group.picking_type_id.display_name, stp3.display_name, stp1.display_name))
            if not group.picking_type_id:
                group.picking_type_id = stp3.id

        if group.picking_id and group.picking_id.picking_type_id and group.picking_id.picking_type_id != stp3:
            raise UserError(_(
                "La agrupación ya tiene un albarán (%s) con tipo '%s'. No se puede usar '%s'."
            ) % (
                group.picking_id.display_name,
                group.picking_id.picking_type_id.display_name,
                stp3.display_name,
            ))

        if not self.mo_ids:
            raise UserError(_("No hay OF seleccionadas para añadir."))

        bad = self.mo_ids.filtered(lambda m: m.picking_type_id and m.picking_type_id != stp1)
        if bad:
            raise UserError(_(
                "Las OF seleccionadas no coinciden con el Tipo de operación '%s'."
            ) % stp1.display_name)

        self.mo_ids.write({"group_id": group.id})
        group._set_start_date_if_empty()

        if created:
            return {
                "type": "ir.actions.act_window",
                "name": _("Agrupación de OF"),
                "res_model": "mrp.production.group",
                "view_mode": "form",
                "res_id": group.id,
                "target": "current",
            }
        return {"type": "ir.actions.act_window_close"}