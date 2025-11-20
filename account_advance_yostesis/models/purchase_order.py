from odoo import api, fields, models
from odoo.tools import float_compare

class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    @api.depends(
        "currency_id", "company_id", "amount_total",
        "account_payment_ids", "account_payment_ids.state",
        "account_payment_ids.move_id", "account_payment_ids.move_id.line_ids",
        "account_payment_ids.move_id.line_ids.date",
        "account_payment_ids.move_id.line_ids.debit",
        "account_payment_ids.move_id.line_ids.credit",
        "account_payment_ids.move_id.line_ids.currency_id",
        "account_payment_ids.move_id.line_ids.amount_currency",
        "order_line.invoice_lines.move_id",
        "order_line.invoice_lines.move_id.amount_total",
        "order_line.invoice_lines.move_id.amount_residual",
    )
    def _compute_purchase_advance_payment(self):
        """
        Recalcula el residual contando los prepagos sobre la CUENTA DESTINO
        del pago (ahora 407), en lugar de filtrar solo cuentas 'payable' (400).
        """
        for order in self:
            # Localiza, para cada pago posteado, la línea en la cuenta destino (ej. 407)
            mls = self.env["account.move.line"]
            for pay in order.account_payment_ids.filtered(lambda p: p.state == "posted"):
                dest_acc_id = pay._get_destination_account_id()
                if dest_acc_id:
                    mls |= pay.move_id.line_ids.filtered(
                        lambda l: l.account_id.id == dest_acc_id and l.parent_state == "posted"
                    )

            advance_amount = 0.0
            for line in mls:
                line_currency = line.currency_id or line.company_id.currency_id
                # tomar el residual (currency si existe) y convertir a la moneda de la OC
                line_amount = (
                    line.amount_residual_currency if line.currency_id else line.amount_residual
                )
                if line_currency != order.currency_id:
                    advance_amount += line_currency._convert(
                        line_amount,
                        order.currency_id,
                        order.company_id,
                        line.date or fields.Date.today(),
                    )
                else:
                    advance_amount += line_amount

            # Pagos aplicados a facturas de la OC (como en el módulo base)
            invoice_paid_amount = 0.0
            for inv in order.invoice_ids:
                invoice_paid_amount += inv.amount_total - inv.amount_residual

            amount_residual = order.amount_total - advance_amount - invoice_paid_amount
            payment_state = "not_paid"
            if mls or not order.currency_id.is_zero(invoice_paid_amount):
                has_due_amount = float_compare(
                    amount_residual, 0.0, precision_rounding=order.currency_id.rounding
                )
                payment_state = "paid" if has_due_amount <= 0 else "partial"

            order.payment_line_ids = mls
            order.amount_residual = amount_residual
            order.advance_payment_status = payment_state
