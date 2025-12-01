from odoo import fields, models

class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"
    x_studio_obs = fields.Char(string="Obs Fabr Producto")
