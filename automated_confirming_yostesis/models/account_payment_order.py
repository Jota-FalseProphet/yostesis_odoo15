from odoo import models, fields, api
from dateutil.relativedelta import relativedelta


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    @api.model
    def _cron_confirming_auto_conciliation(self, from_date=False):
        icp = self.env["ir.config_parameter"].sudo()
        
        enabled = icp.get_param("yostesis_confirming.confirming_enable_cron", "False")
        if enabled not in ("True", "1", True):
            return
        
        today = fields.Date.context_today(self)

        if not from_date:
            from_date_param = icp.get_param("yostesis_confirming.confirming_from_date")
            if from_date_param:
                from_date = fields.Date.to_date(from_date_param)
        elif isinstance(from_date, str):
            from_date = fields.Date.to_date(from_date)

        limit_date = today - relativedelta(days=2)

        payment_mode_param = icp.get_param("yostesis_confirming.confirming_payment_mode_id")
        confirming_payment_mode_id = int(payment_mode_param) if payment_mode_param else False

        risk_account_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        debt_account_param = icp.get_param("yostesis_confirming.confirming_debt_account_id")
        journal_param = icp.get_param("yostesis_confirming.confirming_journal_id")

        if not (risk_account_param and debt_account_param and journal_param):
            return

        Account = self.env["account.account"]
        Journal = self.env["account.journal"]

        risk_account = Account.browse(int(risk_account_param))
        debt_account = Account.browse(int(debt_account_param))
        journal = Journal.browse(int(journal_param))

        if not (risk_account and debt_account and journal):
            return

        domain = [("state", "!=", "draft")]
        if confirming_payment_mode_id:
            domain.append(("payment_mode_id", "=", confirming_payment_mode_id))

        orders = self.search(domain)

        Move = self.env["account.move"]
        MailMessage = self.env["mail.message"]

        for order in orders:
            for payment_line in order.payment_line_ids:
                try:
                    origin_line = payment_line.move_line_id
                    if not origin_line or not origin_line.date_maturity:
                        continue

                    if origin_line.date_maturity > limit_date:
                        continue
                    if from_date and origin_line.date_maturity < from_date:
                        continue

                    full_rec = origin_line.full_reconcile_id
                    if not full_rec:
                        continue

                    related_moves = full_rec.reconciled_line_ids.mapped("move_id")

                    risk_lines = related_moves.mapped("line_ids").filtered(
                        lambda l: l.account_id.id == risk_account.id
                    )

                    if not risk_lines:
                        continue

                    for risk_line in risk_lines:
                        if risk_line.yostesis_confirming_cancel_move_id:
                            continue

                        amount = abs(risk_line.balance)
                        if not amount:
                            continue

                        partner = risk_line.partner_id
                        company = risk_line.company_id

                        vals_move = {
                            "move_type": "entry",
                            "date": origin_line.date_maturity,
                            "journal_id": journal.id,
                            "company_id": company.id,
                            "ref": "Auto factoring cancellation %s" % origin_line.move_id.name,
                            "is_confirming_cancel_move": True,
                            "line_ids": [
                                (0, 0, {
                                    "name": "Factoring bank debt cancellation",
                                    "account_id": risk_account.id,
                                    "partner_id": partner.id,
                                    "debit": amount,
                                    "credit": 0.0,
                                }),
                                (0, 0, {
                                    "name": "Factoring risk reclassification",
                                    "account_id": debt_account.id,
                                    "partner_id": partner.id,
                                    "debit": 0.0,
                                    "credit": amount,
                                }),
                            ],
                        }

                        cancel_move = Move.create(vals_move)

                        if not self.env.context.get("confirming_test_only"):
                            cancel_move.action_post()

                        lines_to_reconcile = risk_line | cancel_move.line_ids.filtered(
                            lambda l: l.account_id.id == risk_account.id
                            and l.partner_id.id == partner.id
                            and l.company_id.id == company.id
                        )
                        lines_to_reconcile = lines_to_reconcile.filtered(
                            lambda l: not l.reconciled and not l.full_reconcile_id
                        )

                        if len(lines_to_reconcile) == 2:
                            lines_to_reconcile.reconcile()

                        risk_line.write({
                            "yostesis_confirming_cancel_move_id": cancel_move.id,
                        })

                        if full_rec:
                            invoice_lines = full_rec.reconciled_line_ids.filtered(
                                lambda l: l.account_internal_type == "receivable"
                                and l.move_id.move_type in ("out_invoice", "out_refund")
                            )
                            if invoice_lines:
                                invoice_lines.write({
                                    "yostesis_confirming_cancel_move_id": cancel_move.id,
                                })

                except Exception as e:
                    MailMessage.create({
                        "model": "account.payment.order",
                        "res_id": order.id,
                        "body": "Error en cron factoring con línea %s: %s" % (payment_line.id, e),
                    })
                    continue
