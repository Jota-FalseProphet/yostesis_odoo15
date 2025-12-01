from odoo import models, fields
# Nuevo atributo para el campo date_planned en purchase.order con tracking, para que aparezca en el chatter al modificarse y sobretodo quien lo ha modificado
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'
    
    # Añadimos tracking al campo date_planned (Fecha de recepción)
    date_planned = fields.Datetime(tracking=True)