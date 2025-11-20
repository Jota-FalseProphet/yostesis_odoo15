from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    account_advance_supplier_id = fields.Many2one(
        related='company_id.account_advance_supplier_id',
        readonly=False
    )
