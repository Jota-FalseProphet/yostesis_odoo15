# -*- coding: utf-8 -*-
from odoo import models, fields, api
from fractions import Fraction

LB_TO_KG = 0.453592


class StockMove(models.Model):
    _inherit = "stock.move"

    kg_line_total = fields.Float(
        string="Kg línea",
        compute="_compute_kg_line_total",
        digits="Product Unit of Measure",
    )

    cbm_line = fields.Float(
        string="Volumen línea (m³)",
        compute="_compute_cbm_line",
        digits=(16, 4),
    )

    @api.depends(
        "product_uom_qty",
        "product_id.product_tmpl_id.lb_paq_total",
        "product_id.weight",
    )
    def _compute_kg_line_total(self):
        for move in self:
            kg = 0.0
            lb_total = getattr(move, "lb_total_pr", False)
            if lb_total:
                kg = lb_total * LB_TO_KG
            else:
                lb_unit = getattr(move.product_id.product_tmpl_id, "lb_paq_total", 0.0)
                if lb_unit:
                    try:
                        lb_unit = float(Fraction(lb_unit))
                    except (ValueError, ZeroDivisionError):
                        lb_unit = float(lb_unit)
                    kg = lb_unit * move.product_uom_qty * LB_TO_KG
                elif move.product_id.weight:
                    kg = move.product_id.weight * move.product_uom_qty
            move.kg_line_total = kg


    @api.depends(
        "product_uom_qty",
        "product_id.product_tmpl_id.measure_data_ids.wide",
        "product_id.product_tmpl_id.measure_data_ids.height",
        "product_id.product_tmpl_id.measure_data_ids.depth",
    )
    def _compute_cbm_line(self):
        
        # Calcula el volumen total de la línea.

        # 1) Suma (wide × height × depth) de cada measure_line.
        # 2) Si no hay measure_data, usa length/width/height de la plantilla.
        # Todas las medidas se esperan en **metros**.
       
        for move in self:
            tmpl = move.product_id.product_tmpl_id
            vol_unit = 0.0

            # Medidas por paquete
            for m in tmpl.measure_data_ids:
                if m.wide and m.height and m.depth:
                    vol_unit += m.wide * m.height * m.depth

            # Medidas estándar de la plantilla
            if not vol_unit and getattr(tmpl, "length", 0) and getattr(tmpl, "width", 0) and getattr(tmpl, "height", 0):
                vol_unit = tmpl.length * tmpl.width * tmpl.height

            move.cbm_line = vol_unit * move.product_uom_qty
