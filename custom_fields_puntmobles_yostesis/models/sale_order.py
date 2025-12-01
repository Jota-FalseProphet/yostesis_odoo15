from odoo import models, fields
# Nuevo atributo para el campo date_order en sale.order con tracking, para que aparezca en el chatter al modificarse y sobretodo quien lo ha modificado
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    
    # Añadimos tracking al campo date_order (Fecha de pedido)
    date_order = fields.Datetime(tracking=True)