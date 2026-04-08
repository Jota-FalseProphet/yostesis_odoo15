from odoo import fields, models


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    prescriptor_id = fields.Many2one(
        comodel_name='res.partner',
        string='Preescriptor',
        domain="[('agent', '=', True), ('agent_type_yostesis_id.name', '=', 'Preescriptor')]",
    )
