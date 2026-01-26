# -*- coding: utf-8 -*-
from collections import defaultdict
from odoo.tools.float_utils import float_is_zero
from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = "stock.picking"

    kg_paq_total_pr = fields.Float(
        string="Peso total (kg)",
        compute="_compute_kg_total",
        digits="Product Unit of Measure",
    )
    cbm_total = fields.Float(
        string="Volumen total (m³)",
        compute="_compute_cbm_total",
        digits="Product Unit of Measure",
    )

    @api.model
    def _is_accessory(self, tmpl):
        Measure = self.env["product.measure.data"]
        recs = Measure.search([("product_tmpl_id", "=", tmpl.id)], limit=1)
        if not recs:
            return False
        m = recs[0]
        return (
            float_is_zero(m.depth,       precision_digits=4)
            and float_is_zero(m.wide,    precision_digits=4)
            and float_is_zero(m.height,  precision_digits=4)
            and float_is_zero(m.package_kg, precision_digits=4)
        )

    @api.depends("move_ids_without_package.kg_line_total")
    def _compute_kg_total(self):
        for picking in self:
            valid_moves = picking.move_ids_without_package.filtered(
                lambda m: not picking._is_accessory(m.product_id.product_tmpl_id)
            )
            picking.kg_paq_total_pr = sum(valid_moves.mapped("kg_line_total"))

    @api.depends("move_ids_without_package.cbm_line")
    def _compute_cbm_total(self):
        for picking in self:
            valid_moves = picking.move_ids_without_package.filtered(
                lambda m: not picking._is_accessory(m.product_id.product_tmpl_id)
            )
            picking.cbm_total = sum(valid_moves.mapped("cbm_line"))

    def get_group_lines(self):
        self.ensure_one()
        groups = {}
        order = []

        for mv in self.move_ids_without_package:
            if self._is_accessory(mv.product_id.product_tmpl_id):
                continue

            qty = mv.quantity_done or mv.product_uom_qty or 0.0

            pkg_type = "BOX"
            ml = mv.move_line_ids[:1]
            if ml and ml.result_package_id and ml.result_package_id.package_type_id:
                pkg_type = ml.result_package_id.package_type_id.name or "BOX"

            key = (mv.product_id.id, pkg_type)
            if key not in groups:
                order.append(key)
                groups[key] = {
                    "pkg_type":  pkg_type,
                    "product":   mv.product_id,
                    "length_cm": mv.length_cm,
                    "width_cm":  mv.width_cm,
                    "height_cm": mv.height_cm,
                    "kg_unit":   mv.kg_unit,
                    "cbm_unit":  mv.cbm_unit,
                    "qty":       0.0,
                    "kg_total":  0.0,
                    "cbm_total": 0.0,
                    "quantity_box": "",
                }
            g = groups[key]
            g["qty"]       += qty
            g["kg_total"]  += mv.kg_line_total
            g["cbm_total"] += mv.cbm_line

        # ───────────────────────────────────────────────────────────────
        #  AÑADIDO → traemos los 'quantity_box' desde product_measure_data
        # ───────────────────────────────────────────────────────────────
        PMD = self.env["product.measure.data"]
        for g in groups.values():
            tmpl = g["product"].product_tmpl_id
            boxes = PMD.search(
                [("product_tmpl_id", "=", tmpl.id)],
                order="id"               # o 'quantity_box' si prefieres
            ).mapped("quantity_box")
            # Unimos todos los valores en la misma celda
            g["quantity_box"] = ", ".join(boxes) if boxes else ""

        # Lista ordenada para la plantilla QWeb
        result = []
        for idx, key in enumerate(order, start=1):
            g = groups[key]
            g["idx"] = idx
            result.append(g)
        return result

