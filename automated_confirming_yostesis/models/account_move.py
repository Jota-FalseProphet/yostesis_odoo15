# Punt_staging3/puntmobles/automated_confirming_yostesis/models/account_move.py


import json

from odoo import models, fields, _
from odoo.tools.misc import format_date


class AccountMove(models.Model):
    _inherit = "account.move"

    confirming_cancel_move_id = fields.Many2one(
        "account.move",
        string="Pago Confirming",
        compute="_compute_confirming_cancel_move_id",
        readonly=True,
    )

    is_confirming_cancel_move = fields.Boolean(
        string="Asiento cancelación Confirming",
        readonly=True,
        copy=False,
    )

    def _compute_confirming_cancel_move_id(self):
        for move in self:
            if move.is_confirming_cancel_move:
                move.confirming_cancel_move_id = False
                continue

            line = move.line_ids.filtered(
                lambda l: l.yostesis_confirming_cancel_move_id
            )[:1]
            move.confirming_cancel_move_id = (
                line.yostesis_confirming_cancel_move_id if line else False
            )

    def _compute_payment_state(self):
        super()._compute_payment_state()

        for move in self:
            if move.move_type not in (
                "out_invoice",
                "in_invoice",
                "out_refund",
                "in_refund",
            ):
                continue

            if move.payment_state != "in_payment":
                continue

            if (
                move.confirming_cancel_move_id
                and fields.Float.is_zero(
                    move.amount_residual,
                    precision_rounding=move.currency_id.rounding,
                )
            ):
                move.payment_state = "paid"

    def _compute_payments_widget_reconciled_info(self):
        super()._compute_payments_widget_reconciled_info()

        for move in self:
            cancel_move = move.confirming_cancel_move_id
            if not cancel_move:
                continue

            widget_value = move.invoice_payments_widget
            if not widget_value or widget_value in ("false", "False"):
                data = {"title": "", "outstanding": False, "content": []}
                original_is_str = True
            elif isinstance(widget_value, str):
                data = json.loads(widget_value)
                original_is_str = True
            else:
                data = widget_value
                original_is_str = False

            content = data.setdefault("content", [])

            if any(line.get("move_id") == cancel_move.id for line in content):
                move.invoice_payments_widget = (
                    json.dumps(data) if original_is_str else data
                )
                continue

            template = (content[0] if content else {}) or {}

            amount = abs(cancel_move.amount_total_signed or move.amount_total_signed)
            currency = move.currency_id

            new_line = dict(template)

            for key in ("payment_id", "move_line_id", "group_id", "account_payment_id"):
                new_line.pop(key, None)

            maturity_date = move.invoice_date_due or cancel_move.date
            maturity_str = fields.Date.to_string(maturity_date)
            maturity_label = format_date(self.env, maturity_date)

            new_line.update(
                {
                    "move_id": cancel_move.id,
                    "amount": amount,
                    "date": maturity_str,
                    "ref": cancel_move.ref or cancel_move.name,
                    "journal_name": cancel_move.journal_id.display_name,
                }
            )

            new_line["name"] = _("Pagado al Vencimiento en %s") % maturity_label
            new_line["is_confirming"] = True 

            if "currency_id" in template:
                new_line["currency_id"] = currency.id
            if "currency" in template:
                new_line["currency"] = currency.symbol

            content.append(new_line)

            move.invoice_payments_widget = (
                json.dumps(data) if original_is_str else data
            )
