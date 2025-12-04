from odoo import models, fields

class SaleOrderProject(models.Model):
    _name = 'sale.order.project'
    _description = 'Nombre/Referencia del proyecto'
    _order = 'name'
    
    name =fields.Char(required=True)
    active = fields.Boolean(default=True)
    
    
    
class SaleOrder(models.Model):
    _inherit = 'sale.order'
    # En ir.model.acces.csv se da acceso al modelo sale.order.project en la línea 2 
    project_id = fields.Many2one(
        'sale.order.project', 
        string = 'Nombre/Ref del proyecto'
    )
    
    
   