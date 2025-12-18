from odoo import models, fields

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Añadido tracking al campo default_code (Referencia interna)   
    default_code = fields.Char(tracking=True)