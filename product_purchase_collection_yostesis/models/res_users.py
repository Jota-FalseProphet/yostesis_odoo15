from odoo import models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    allow_create_purchase_collection = fields.Boolean(
        string="Puede gestionar colecciones de compra",
    )
