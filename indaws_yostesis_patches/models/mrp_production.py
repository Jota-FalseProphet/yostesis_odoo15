from odoo import api, fields, models

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    # El módulo indaws_internal_reference añade en mrp.production los campos computados 
    # y no almacenados origin_sale y sale_line_id .
    # Esos campos se muestran en las vistas (form y tree) de mrp.production que hereda el módulo.

    # El log dice:
    # Non-stored field mrp.production.sale_line_id cannot be searched.
    # es decir que Odoo intentó buscar/ordenar/agrupar por ese campo, cosa que no se puede al no estar store=True.

    # Cuando el backend lanza esa excepción, el cliente web puede enseñarle a la usuaria un mensaje genérico de “sin permisos” 
    # o un modal de error, 
    # bloqueando la pantalla, aunque no sea un AccessError.

    origin_sale = fields.Many2one(
        comodel_name="sale.order",
        string="Origin Sale",
        compute="_compute_origin_sale",  
        store=True,   # no estaba
        readonly=True,
        index=True,
    )

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Origin Sale Line",
        compute="_compute_origin_sale",  
        store=True,   # no estaba
        readonly=True,
        index=True,
    )
