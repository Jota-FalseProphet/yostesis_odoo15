# -*- coding: utf-8 -*-
from odoo import models, fields

class StockMoveLine(models.Model):
    _inherit = "stock.move.line"

    length_cm   = fields.Float(related="move_id.length_cm",   readonly=True)
    width_cm    = fields.Float(related="move_id.width_cm",    readonly=True)
    height_cm   = fields.Float(related="move_id.height_cm",   readonly=True)

    kg_unit       = fields.Float(related="move_id.kg_unit",       readonly=True)
    kg_line_total = fields.Float(related="move_id.kg_line_total", readonly=True)

    cbm_unit  = fields.Float(related="move_id.cbm_unit",  readonly=True)
    cbm_line  = fields.Float(related="move_id.cbm_line",  readonly=True)
