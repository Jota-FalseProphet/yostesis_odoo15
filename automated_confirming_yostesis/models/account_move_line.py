from odoo import models, fields

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    yostesis_confirming_cancel_move_id = fields.Many2one(
        "account.move",
        string="Confirming Cancel Move",
        readonly=True
    )
