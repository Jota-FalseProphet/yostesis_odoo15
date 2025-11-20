from odoo import models


class ProductTemplateAttributeLine(models.Model):
    _inherit = "product.template.attribute.line"
    # This model is used to patch the SQL constraint message in product_variant_configurator
    _sql_constraints = [] 
