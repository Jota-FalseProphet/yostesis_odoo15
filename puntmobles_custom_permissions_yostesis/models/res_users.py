from odoo import models, fields

class ResUsers(models.Model):
    _inherit = 'res.users'

    restrict_confirm_sale = fields.Boolean(string="Restringir confirmación de pedidos")

    allow_change_confirmed_sale_customer = fields.Boolean(
        string="Puede cambiar cliente en pedidos confirmados"
    )