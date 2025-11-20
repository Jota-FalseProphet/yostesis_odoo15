from odoo import models
from odoo.exceptions import UserError

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    def action_confirm(self):
        if self.env.user.restrict_confirm_sale:
            raise UserError("No tienes permiso para confirmar pedidos de venta.")
        return super(SaleOrder, self).action_confirm()
