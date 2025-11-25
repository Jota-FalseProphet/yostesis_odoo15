from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _simple_customer_payment_apply_if_needed(self):
        moves = self.filtered(lambda m: m.state == "posted" and m.move_type == "entry")
        if not moves:
            return

        Payment = self.env["account.payment"]
        Account = self.env["account.account"]

        for move in moves:
            pay = Payment.search([("move_id", "=", move.id)], limit=1)
            if not pay:
                continue

            if pay.partner_type != "customer":
                continue
            if pay.payment_type != "inbound":
                continue
            if pay.is_advance:
                continue
            if move.payment_order_id:
                continue

            line_4311 = move.line_ids.filtered(
                lambda l: l.account_id.code
                and l.account_id.code.startswith("4311")
            )[:1]

            recv_lines = move.line_ids.filtered(
                lambda l: l.account_internal_type == "receivable"
            )

            if not line_4311 or not recv_lines:
                continue

            acc_4312 = Account.search(
                [
                    ("code", "like", "4312%"),
                    ("company_id", "=", move.company_id.id),
                ],
                limit=1,
            )
            if not acc_4312:
                continue

            line_4311.with_context(
                skip_account_move_synchronization=True
            ).write(
                {"account_id": acc_4312.id}
            )
