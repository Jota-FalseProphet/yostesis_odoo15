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

    # ------------------------------------------------------------------
    # LOCALIZAR ASIENTO DE CANCELACIÓN (PAGO AL VENCIMIENTO)
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # ESTADO DE PAGO CON RIESGO CONFIRMING
    # ------------------------------------------------------------------
    def _compute_payment_state(self):
        """
        - Si hay riesgo de confirming (4311) aún abierto, la factura debe
          permanecer en 'in_payment' aunque esté totalmente conciliada.

        - Cuando exista 'confirming_cancel_move_id' y el residual sea 0,
          pasa definitivamente a 'paid'.
        """
        super()._compute_payment_state()

        icp = self.env["ir.config_parameter"].sudo()
        risk_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        risk_account = (
            self.env["account.account"].browse(int(risk_param))
            if risk_param
            else self.env["account.account"].browse()
        )

        for move in self:
            if move.move_type not in (
                "out_invoice",
                "in_invoice",
                "out_refund",
                "in_refund",
            ):
                continue

            # 1) Hay riesgo 4311 vivo → estado forzado a in_payment
            if move.payment_state == "paid" and risk_account:
                recv_pay_lines = move.line_ids.filtered(
                    lambda l: l.account_internal_type in ("receivable", "payable")
                )
                full_recs = recv_pay_lines.mapped("full_reconcile_id")
                if full_recs:
                    risk_lines = full_recs.mapped("reconciled_line_ids").filtered(
                        lambda l: l.account_id.id == risk_account.id
                        and not l.yostesis_confirming_cancel_move_id
                    )
                    if risk_lines:
                        move.payment_state = "in_payment"

            # 2) Cuando ya existe cancelación y residual 0 → paid
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

    # ------------------------------------------------------------------
    # WIDGET DE PAGOS EN LA FACTURA
    # ------------------------------------------------------------------
    def _compute_payments_widget_reconciled_info(self):
        """
        Extiende el widget de pagos para el caso confirming:

        - Marca las líneas de RIESGO (4311) como 'is_confirming_risk'
          para poder cambiar el texto en el widget (por ejemplo,
          "En remesa (factoring) el ...").

        - Añade una línea virtual cuando existe el asiento de
          cancelación (pago al vencimiento), con el texto:
          "Pagado al Vencimiento en ...".
        """
        super()._compute_payments_widget_reconciled_info()

        icp = self.env["ir.config_parameter"].sudo()
        risk_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        risk_account = (
            self.env["account.account"].browse(int(risk_param))
            if risk_param
            else self.env["account.account"].browse()
        )

        Move = self.env["account.move"]

        for move in self:
            # ----------------------------------------------------------
            # Normalizar widget_value a dict
            # ----------------------------------------------------------
            widget_value = move.invoice_payments_widget
            if not widget_value or widget_value in ("false", "False"):
                data = {"title": "", "outstanding": False, "content": []}
                original_is_str = True
            elif isinstance(widget_value, str):
                try:
                    data = json.loads(widget_value)
                except Exception:
                    data = {"title": "", "outstanding": False, "content": []}
                original_is_str = True
            else:
                data = widget_value
                original_is_str = False

            content = data.setdefault("content", [])

            # ----------------------------------------------------------
            # 1) Marcar líneas de REMESA (riesgo confirming 4311)
            # ----------------------------------------------------------
            if risk_account:
                for line_dict in content:
                    move_id = line_dict.get("move_id")
                    if not move_id:
                        continue

                    pay_move = Move.browse(move_id)
                    if not pay_move:
                        continue

                    # ¿Este apunte forma parte del asiento de riesgo?
                    risk_lines = pay_move.line_ids.filtered(
                        lambda l: l.account_id.id == risk_account.id
                        and not l.yostesis_confirming_cancel_move_id
                    )
                    if not risk_lines:
                        continue

                    # Lo marcamos para el QWeb del widget
                    line_dict["is_confirming_risk"] = True

                    # Texto más adecuado para remesa (opcional, por si el
                    # template usa line.name).
                    maturity_date = move.invoice_date_due or pay_move.date
                    maturity_label = format_date(self.env, maturity_date)
                    line_dict["name"] = _(
                        "En remesa (factoring) con vto. %s"
                    ) % maturity_label

            # ----------------------------------------------------------
            # 2) Añadir línea virtual de PAGO AL VENCIMIENTO
            # ----------------------------------------------------------
            cancel_move = move.confirming_cancel_move_id
            if cancel_move:
                # ¿ya existe una línea en el widget para este asiento?
                if any(
                    line.get("move_id") == cancel_move.id for line in content
                ):
                    move.invoice_payments_widget = (
                        json.dumps(data) if original_is_str else data
                    )
                    continue

                template = (content[0] if content else {}) or {}
                new_line = dict(template)

                # Limpiar claves específicas de pago
                for key in (
                    "payment_id",
                    "move_line_id",
                    "group_id",
                    "account_payment_id",
                ):
                    new_line.pop(key, None)

                amount = abs(
                    cancel_move.amount_total_signed or move.amount_total_signed
                )
                currency = move.currency_id

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
                        "name": _("Pagado al Vencimiento en %s") % maturity_label,
                        "is_confirming": True,
                    }
                )

                if "currency_id" in template:
                    new_line["currency_id"] = currency.id
                if "currency" in template:
                    new_line["currency"] = currency.symbol

                content.append(new_line)

            # ----------------------------------------------------------
            # Guardar de vuelta en el campo compute
            # ----------------------------------------------------------
            move.invoice_payments_widget = (
                json.dumps(data) if original_is_str else data
            )
