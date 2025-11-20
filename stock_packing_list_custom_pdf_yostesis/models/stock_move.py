# models/stock_move.py
# -*- coding: utf-8 -*-
from odoo import models, fields, api
from fractions import Fraction

LB_TO_KG = 0.453592


class StockMove(models.Model):
    _inherit = "stock.move"

    kg_unit       = fields.Float(string="Kg por bulto",   compute="_compute_physical_values",
                                 digits="Product Unit of Measure")
    kg_line_total = fields.Float(string="Kg línea",       compute="_compute_physical_values",
                                 digits="Product Unit of Measure")
    cbm_unit      = fields.Float(string="Volumen por bulto (m³)", compute="_compute_physical_values",
                                 digits=(16, 4))
    cbm_line      = fields.Float(string="Volumen línea (m³)",      compute="_compute_physical_values",
                                 digits=(16, 4))

    length_cm = fields.Float(string="Largo (cm)",  compute="_compute_physical_values", digits=(16, 2))
    width_cm  = fields.Float(string="Ancho (cm)",  compute="_compute_physical_values", digits=(16, 2))
    height_cm = fields.Float(string="Alto (cm)",   compute="_compute_physical_values", digits=(16, 2))

    @api.depends(
        "product_uom_qty",
        "product_id.weight",
        "product_id.product_tmpl_id.lb_paq_total",
        "product_id.product_tmpl_id.measure_data_ids.wide",
        "product_id.product_tmpl_id.measure_data_ids.height",
        "product_id.product_tmpl_id.measure_data_ids.depth",
    )
    def _compute_physical_values(self):
        """
        Valores calculados a partir de:
        - Peso → lb_total_pr (si existe) o lb_paq_total / weight.
        - Volumen → medida Wide × Height × Depth *(primer registro)*.
        - Dimensiones (cm) → Wide / Depth / Height *(primer registro)*.
        """
        for move in self:
            tmpl = move.product_id.product_tmpl_id

            if getattr(move, "lb_total_pr", False):
                kg_unit = move.lb_total_pr * LB_TO_KG
            else:
                lb_unit = getattr(tmpl, "lb_paq_total", 0.0)
                if lb_unit:
                    try:
                        lb_unit = float(Fraction(lb_unit))
                    except (ValueError, ZeroDivisionError):
                        lb_unit = float(lb_unit)
                    kg_unit = lb_unit * LB_TO_KG
                else:
                    kg_unit = move.product_id.weight or 0.0

            mline = tmpl.measure_data_ids[:1]
            if mline:
                wide   = mline.wide   or 0.0
                depth  = mline.depth  or 0.0
                height = mline.height or 0.0

                vol_unit         = wide * depth * height
                move.length_cm   = wide   * 100.0
                move.width_cm    = depth  * 100.0
                move.height_cm   = height * 100.0
            else:
                vol_unit = 0.0
                move.length_cm = move.width_cm = move.height_cm = 0.0

            qty = move.quantity_done or move.product_uom_qty or 0.0
            move.kg_unit       = kg_unit
            move.kg_line_total = kg_unit * qty
            move.cbm_unit      = vol_unit
            move.cbm_line      = vol_unit * qty
