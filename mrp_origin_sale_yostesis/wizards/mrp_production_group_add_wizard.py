import re

from odoo import api, fields, models, _
from dateutil.relativedelta import relativedelta


class MrpProductionGroupAddWizard(models.TransientModel):
    _inherit = "mrp.production.group.add.wizard"

    commitment_date_from = fields.Date(
        string="Fecha ent prev PV desde"
    )
    commitment_date_to = fields.Date(
        string="Fecha ent prev PV hasta"
    )

    origin_date_expected_from = fields.Date(
        string="Fecha ent prev desde"
    )
    origin_date_expected_to = fields.Date(
        string="Fecha ent prev hasta"
    )

    origin_product_ids = fields.Many2many(
        comodel_name="product.product",
        relation="mpg_wiz_origin_product_rel",
        column1="wizard_id",
        column2="product_id",
        string="Producto Padre",
    )

    display_origin_search = fields.Char(
        string="Origen Absoluto",
        help="Busca por origen absoluto (PV, PC, OF). Varios tokens separados por espacios/comas (OR).",
    )

    coleccion_search = fields.Char(
        string="Colección",
        help="Busca por colección del producto. Varios tokens separados por espacios/comas (OR).",
    )

    def _base_domain(self):
        dom = super()._base_domain()

        if self.display_origin_search:
            raw = self.display_origin_search.strip()
            tokens = [t for t in re.split(r"[,\s;]+", raw) if t]
            if tokens:
                terms = []
                for t in tokens:
                    terms.append(("display_origin_name", "ilike", t))
                dom += self._or_domain_terms(terms)

        if self.commitment_date_from:
            dom.append(("sale_commitment_date", ">=", fields.Datetime.to_datetime(self.commitment_date_from)))
        if self.commitment_date_to:
            dt_to = fields.Datetime.to_datetime(self.commitment_date_to) + relativedelta(days=1)
            dom.append(("sale_commitment_date", "<", dt_to))

        if self.origin_date_expected_from:
            dom.append(("origin_date_expected", ">=", fields.Datetime.to_datetime(self.origin_date_expected_from)))
        if self.origin_date_expected_to:
            dt_to = fields.Datetime.to_datetime(self.origin_date_expected_to) + relativedelta(days=1)
            dom.append(("origin_date_expected", "<", dt_to))

        if self.origin_product_ids:
            dom.append(("origin_product_id", "in", self.origin_product_ids.ids))

        if self.coleccion_search:
            raw = self.coleccion_search.strip()
            tokens = [t for t in re.split(r"[,\s;]+", raw) if t]
            if tokens:
                paths = ["product_id.product_tmpl_id.x_studio_coleccion"]
                MO = self.env["mrp.production"]
                if "origin_product_id" in MO._fields:
                    paths.append("origin_product_id.product_tmpl_id.x_studio_coleccion")
                terms = []
                for p in paths:
                    for t in tokens:
                        terms.append((p, "ilike", t))
                dom += self._or_domain_terms(terms)

        return dom

    def _code_prefix_search_paths(self):
        paths = super()._code_prefix_search_paths()
        MO = self.env["mrp.production"]
        PT = self.env["product.template"]
        if "origin_product_id" in MO._fields:
            f_cp = PT._fields.get("code_prefix")
            if f_cp and f_cp.type == "many2one":
                paths.append("origin_product_id.product_tmpl_id.code_prefix.name")
            elif f_cp:
                paths.append("origin_product_id.product_tmpl_id.code_prefix")
        return paths

    @api.onchange("commitment_date_from", "commitment_date_to", "origin_date_expected_from", "origin_date_expected_to", "origin_product_ids", "coleccion_search", "display_origin_search")
    def _onchange_origin_sale_filters(self):
        for w in self:
            w.warning_msg = _("Filtros cambiados. Pulsa 'Buscar' para recalcular.")
            w.mo_ids = [(5, 0, 0)]
