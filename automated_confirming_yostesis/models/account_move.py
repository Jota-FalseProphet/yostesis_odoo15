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
        """
        Extiende el cómputo estándar de estado de pago para el caso de confirming.

        - Si hay riesgo de confirming (4311) aún abierto, la factura debe
          permanecer en 'in_payment', incluso aunque esté completamente conciliada
          y existan otros cobros (anticipos, pagos reales, etc.).

        - Cuando exista 'confirming_cancel_move_id' y el residual sea 0, se
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

            # 1) Si Odoo la ha marcado como 'paid' pero todavía hay riesgo
            #    de confirming sin asiento de cancelación, la forzamos a
            #    'in_payment'. Esto cubre el caso "anticipo + confirming".
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

            # 2) Cuando ya existe el asiento de cancelación y residual 0 → 'paid'
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
        """
        - Conserva el comportamiento estándar del widget de pagos.
        - Añade una línea virtual cuando existe el asiento de cancelación de confirming
          ('Pagado al Vencimiento en ...').
        - Marca las líneas de remesa (movimiento con 4311 al DEBE) como "remesa en
          proceso de cobro", modificando el payment_method_name.
        """
        super()._compute_payments_widget_reconciled_info()

        Move = self.env["account.move"]
        icp = self.env["ir.config_parameter"].sudo()
        risk_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        risk_account = (
            self.env["account.account"].browse(int(risk_param))
            if risk_param
            else self.env["account.account"].browse()
        )

        for move in self:
            cancel_move = move.confirming_cancel_move_id

            # --- 1) Leer el widget actual ---
            widget_value = move.invoice_payments_widget
            if not widget_value or widget_value in ("false", "False"):
                data = {"title": "", "outstanding": False, "content": []}
                original_is_str = True
            elif isinstance(widget_value, str):
                try:
                    data = json.loads(widget_value)
                except Exception:
                    # Si por lo que sea está corrupto, no tocamos nada
                    continue
                original_is_str = True
            else:
                data = widget_value
                original_is_str = False

            content = data.setdefault("content", [])

            # --- 2) Añadir línea virtual de cancelación de confirming, si aplica ---
            if cancel_move:
                if not any(line.get("move_id") == cancel_move.id for line in content):
                    template = (content[0] if content else {}) or {}

                    amount = abs(
                        cancel_move.amount_total_signed or move.amount_total_signed
                    )
                    currency = move.currency_id

                    new_line = dict(template)

                    for key in (
                        "payment_id",
                        "move_line_id",
                        "group_id",
                        "account_payment_id",
                    ):
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

                    new_line["name"] = _(
                        "Pagado al Vencimiento en %s"
                    ) % maturity_label
                    new_line["is_confirming"] = True

                    if "currency_id" in template:
                        new_line["currency_id"] = currency.id
                    if "currency" in template:
                        new_line["currency"] = currency.symbol

                    content.append(new_line)

            # --- 3) Marcar líneas de RIESGO de confirming (remesa) ---
            # Queremos localizar el apunte de la remesa (efecto descontado):
            # asiento que tenga la 4311 AL DEBE (riesgo) → esa línea del widget
            # la marcamos como "remesa en proceso de cobro".
            if risk_account:
                for line_dict in content:
                    move_id = line_dict.get("move_id")
                    if not move_id:
                        continue

                    pay_move = Move.browse(move_id)
                    if not pay_move:
                        continue

                    risk_line = pay_move.line_ids.filtered(
                        lambda l: l.account_id.id == risk_account.id and l.debit > 0.0
                    )
                    if not risk_line:
                        continue

                    line_dict["is_confirming_risk"] = True

                    remesa_date = pay_move.date
                    remesa_label = format_date(self.env, remesa_date)
                    line_dict["name"] = _("Remesado en %s") % remesa_label

                    base_label = _("Remesa en proceso de cobro")
                    pm_name = line_dict.get("payment_method_name")
                    if pm_name:
                        line_dict["payment_method_name"] = "%s - %s" % (
                            base_label,
                            pm_name,
                        )
                    else:
                        line_dict["payment_method_name"] = base_label

            # --- 4) Volcar de nuevo el widget si lo tratábamos como str ---
            move.invoice_payments_widget = (
                json.dumps(data) if original_is_str else data
            )

    def _get_reconciled_info_JSON_values(self):
        reconciled_vals = super()._get_reconciled_info_JSON_values()

        if self.move_type not in ("out_invoice", "in_invoice", "out_refund", "in_refund"):
            return reconciled_vals

        icp = self.env["ir.config_parameter"].sudo()
        risk_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        risk_account = (
            self.env["account.account"].browse(int(risk_param))
            if risk_param
            else self.env["account.account"].browse()
        )

        cancel_move = self.confirming_cancel_move_id

        if risk_account:
            for val in reconciled_vals:
                move_id = val.get("move_id")
                if not move_id:
                    continue
                pay_move = self.env["account.move"].browse(move_id)
                if not pay_move:
                    continue
                risk_line = pay_move.line_ids.filtered(
                    lambda l: l.account_id.id == risk_account.id and l.debit > 0.0
                )
                if risk_line:
                    val["is_confirming_risk"] = True
                    remesa_date = pay_move.date
                    remesa_label = format_date(self.env, remesa_date)
                    val["name"] = _("Remesado en %s") % remesa_label

        if cancel_move:
            if not any(v.get("move_id") == cancel_move.id for v in reconciled_vals):
                maturity_date = self.invoice_date_due or cancel_move.date
                maturity_str = fields.Date.to_string(maturity_date)

                template = (reconciled_vals[0] if reconciled_vals else {}) or {}
                new_val = dict(template)
                for key in ("payment_id", "move_line_id", "group_id", "account_payment_id", "partial_id", "is_confirming_risk"):
                    new_val.pop(key, None)

                new_val.update({
                    "move_id": cancel_move.id,
                    "amount": abs(cancel_move.amount_total_signed or self.amount_total_signed),
                    "date": maturity_str,
                    "ref": cancel_move.ref or cancel_move.name,
                    "journal_name": cancel_move.journal_id.display_name,
                    "is_confirming": True,
                })
                reconciled_vals.append(new_val)

        return reconciled_vals
