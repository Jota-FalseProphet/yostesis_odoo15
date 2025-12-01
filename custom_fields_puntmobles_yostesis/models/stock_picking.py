from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    #check de retendido por el transportista stock_picking_views.xml/
    # <xpath expr="//field[@name='carrier_id']" position="after">
    #             <field name="retenido_transportista"/>
    #         </xpath>
    retenido_transportista = fields.Boolean(string="Retenido por transportista")

    # dummy field para que el usuario referencie el albarán de proveedor
    # <xpath expr="//sheet//field[@name='owner_id']" position="after">
    #     <field name="vendor_delivery_note"
    #   </xpath>
    vendor_delivery_note = fields.Char(string="Albarán de proveedor")
