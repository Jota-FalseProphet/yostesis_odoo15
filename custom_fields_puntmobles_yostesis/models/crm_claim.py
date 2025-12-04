from odoo import models, fields

class CrmClaim(models.Model):
    _inherit = 'crm.claim'
    
    # Campo nuevo duplicado de CRM Claim para seleccionar lineas de pedido de venta
    # views/crm_claim_views.xml
    sale_order_for_replace_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta de reemplazo"
    )
    
    sale_order_line_for_replace_id = fields.Many2one(
        "sale.order.line",
        string="Línea de pedido de venta de reemplazo"
    )
    
    cost_currency_id = fields.Many2one(
        "res.currency",
        string="Moneda",
        default= lambda self: self.env.company.currency_id,
        required=True,
    )
    
    cost_amount = fields.Monetary(
        string="Coste",
        currency_field="cost_currency_id",
    )
        
    