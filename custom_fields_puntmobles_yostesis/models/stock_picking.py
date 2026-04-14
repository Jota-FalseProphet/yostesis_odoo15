from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    #check de retendido por el transportista stock_picking_views.xml/
    # <xpath expr="//field[@name='carrier_id']" position="after">
    #             <field name="retenido_transportista"/>
    #         </xpath>
    retenido_transportista = fields.Boolean(string="Retenido por transportista", tracking=True)

    # dummy field para que el usuario referencie el albarán de proveedor
    # <xpath expr="//sheet//field[@name='owner_id']" position="after">
    #     <field name="vendor_delivery_note"
    #   </xpath>
    vendor_delivery_note = fields.Char(string="Albarán de proveedor")

    # Pedido de compra origen para devoluciones a proveedor
    return_purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Pedido de compra origen',
        compute='_compute_return_purchase_order',
    )

    @api.depends('move_lines.origin_returned_move_id.purchase_line_id.order_id')
    def _compute_return_purchase_order(self):
        for picking in self:
            po = picking.move_lines.origin_returned_move_id.purchase_line_id.order_id[:1]
            picking.return_purchase_order_id = po
