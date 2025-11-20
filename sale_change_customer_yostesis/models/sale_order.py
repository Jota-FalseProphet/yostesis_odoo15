from odoo import models, fields, api

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    can_change_customer_by_user = fields.Boolean(
        compute='_compute_can_change_customer_by_user',
        compute_sudo=False
    )

    @api.depends_context('uid')
    def _compute_can_change_customer_by_user(self):
        user = self.env.user
        allow = bool(getattr(user, 'allow_change_confirmed_sale_customer', False))
        for order in self:
            order.can_change_customer_by_user = allow
