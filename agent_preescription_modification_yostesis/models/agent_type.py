from odoo import fields, models


class AgentTypeYostesis(models.Model):
    _name = 'agent.type.yostesis'
    _description = 'Tipo de Agente'

    name = fields.Char(string='Nombre', required=True, translate=True)
