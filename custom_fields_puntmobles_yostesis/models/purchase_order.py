from odoo import models, fields, api, _
from odoo.exceptions import UserError


# Nuevo atributo para el campo date_planned en purchase.order con tracking, para que aparezca en el chatter al modificarse y sobretodo quien lo ha modificado
class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    # Añadimos tracking al campo date_planned (Fecha de recepción → "Fecha prevista")
    date_planned = fields.Datetime(tracking=True)

    @api.depends('order_line.date_planned')
    def _compute_date_planned(self):
        # En pedidos confirmados (purchase/done) no recalculamos date_planned
        # automáticamente al cambiar líneas/precios/cantidades. El usuario puede
        # seguir editándolo manualmente desde la vista (readonly=False).
        confirmed = self.filtered(lambda o: o.state in ('purchase', 'done'))
        super(PurchaseOrder, self - confirmed)._compute_date_planned()

    def button_confirm(self):
        for order in self:
            lines_sin_importe = order.order_line.filtered(
                lambda l: l.product_qty > 0 and l.price_subtotal <= 0
            )
            if lines_sin_importe:
                productos = ', '.join(
                    l.product_id.display_name or l.name
                    for l in lines_sin_importe
                )
                raise UserError(_(
                    'No se puede confirmar el pedido %s porque las '
                    'siguientes líneas tienen un subtotal igual a 0:\n\n%s'
                ) % (order.name, productos))
        return super().button_confirm()

    