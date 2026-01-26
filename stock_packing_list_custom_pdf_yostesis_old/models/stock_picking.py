# -*- coding: utf-8 -*-
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
        digits=(16, 4),
    )

    @api.depends("move_ids_without_package.kg_line_total")
    def _compute_kg_total(self):
        for picking in self:
            picking.kg_paq_total_pr = sum(
                picking.move_ids_without_package.mapped("kg_line_total")
            )


    @api.depends("move_ids_without_package.cbm_line")
    def _compute_cbm_total(self):
        for picking in self:
            picking.cbm_total = sum(
                picking.move_ids_without_package.mapped("cbm_line")
            )
