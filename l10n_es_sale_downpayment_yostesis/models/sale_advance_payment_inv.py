# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class SaleAdvancePaymentInv(models.TransientModel):
    _inherit = "sale.advance.payment.inv"

    pmx_mix_blocked = fields.Boolean(compute="_compute_pmx_mix")
    pmx_mix_message = fields.Html(compute="_compute_pmx_mix")

    def _active_sale_orders(self):
        ids = self.env.context.get("active_ids") or []
        return self.env["sale.order"].browse(ids).exists()

    @api.depends("advance_payment_method")
    def _compute_pmx_mix(self):
        orders = self._active_sale_orders()
        for w in self:
            # Solo aplica cuando se intenta crear DOWN PAYMENT (fixed/percentage).
            if w.advance_payment_method not in ("fixed", "percentage"):
                w.pmx_mix_blocked = False
                w.pmx_mix_message = False
                continue

            conflict = orders.filtered(lambda so: so.advance_amount_paid_order and so.advance_amount_paid_order > 0)
            if conflict:
                w.pmx_mix_blocked = True
                w.pmx_mix_message = _(
                    "<b>No puedes crear un Down Payment</b> en un pedido que ya usa "
                    "<b>anticipo simple (advance payment)</b>.<br/>"
                    "Motivo: se mezclan dos flujos distintos y luego fallan conciliaciones y/o el widget de créditos pendientes.<br/>"
                    "Solución: termina el flujo actual o usa un único sistema para anticipos en este pedido."
                )
            else:
                w.pmx_mix_blocked = False
                w.pmx_mix_message = False

    def create_invoices(self):
        orders = self._active_sale_orders()
        if self.advance_payment_method in ("fixed", "percentage"):
            conflict = orders.filtered(lambda so: so.advance_amount_paid_order and so.advance_amount_paid_order > 0)
            if conflict:
                raise UserError(_(
                    "No puedes crear un Down Payment en un pedido que ya usa anticipo simple (advance payment).\n"
                    "Motivo: se mezclan dos flujos distintos y luego fallan conciliaciones y/o el widget de créditos pendientes.\n"
                    "Solución: termina el flujo actual o usa un único sistema para anticipos en este pedido."
                ))
        return super().create_invoices()
