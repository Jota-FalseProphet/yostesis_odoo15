from odoo import models, fields

class MrpWorkorder(models.Model):
    _inherit = 'mrp.workorder'

    # Observación de la línea de venta (si la OF viene de un pedido)
    x_sale_line_obs = fields.Char(
        related='production_id.sale_line_id.x_studio_obs',
        string='Obs Fabr Producto',
        store=False,  # pon True si quieres poder buscar/ordenar por esta columna
        readonly=True,
    )
