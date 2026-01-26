from odoo import fields, models

class StockMove(models.Model):
    _inherit = "stock.move"

    pmx_operations_total_display = fields.Char(
        related="picking_id.pmx_operations_total_display",
        readonly=True,
        string="Total de Operaciones",
    )
