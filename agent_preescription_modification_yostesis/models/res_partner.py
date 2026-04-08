from odoo import fields, models


class ResPartner(models.Model):
    _inherit = 'res.partner'

    agent_type_yostesis_id = fields.Many2one(
        comodel_name='agent.type.yostesis',
        string='Tipo de Agente',
    )
