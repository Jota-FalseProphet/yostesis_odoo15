from odoo import models, fields


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    purchase_collection = fields.Many2one(
        'purchase.collection',
        string="Colección Compra",
    )
