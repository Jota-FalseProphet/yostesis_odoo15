from odoo import models, fields, api
from dateutil.relativedelta import relativedelta
import zlib


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

        risk_account = self.env["account.account"].browse(int(risk_account_param))
        debt_account = self.env["account.account"].browse(int(debt_account_param))
        journal = self.env["account.journal"].browse(int(journal_param))

        if not (risk_account and debt_account and journal):
            return

        domain = [("state", "!=", "draft")]
        if confirming_payment_mode_id:
            domain.append(("payment_mode_id", "=", confirming_payment_mode_id))

        orders = self.search(domain)

        Move = self.env["account.move"].sudo()
        MailMessage = self.env["mail.message"].sudo()

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
                    all_lines = related_moves.mapped("line_ids")

                    risk_lines = all_lines.filtered(
                        lambda l: l.account_id.id == risk_account.id
                        and not l.move_id.is_confirming_cancel_move
                        and not l.reconciled
                        and not l.full_reconcile_id
                    )

                    if not risk_lines:
                        continue

                    ref = "Auto factoring cancellation %s" % origin_line.move_id.name
                    company = origin_line.company_id

                    lock_key = zlib.crc32(ref.encode("utf-8")) & 0x7FFFFFFF
                    self.env.cr.execute(
                        "SELECT pg_advisory_xact_lock(%s, %s)",
                        (company.id, lock_key),
                    )

                    cancel_move = Move.search([
                        ("is_confirming_cancel_move", "=", True),
                        ("company_id", "=", company.id),
                        ("ref", "=", ref),
                    ], limit=1)

                    risk_lines = risk_lines.filtered(lambda l: not l.yostesis_confirming_cancel_move_id)
                    if not risk_lines:
                        continue

                    by_partner = {}
                    for rl in risk_lines:
                        pid = rl.partner_id.id or 0
                        by_partner.setdefault(pid, self.env["account.move.line"].browse())
                        by_partner[pid] |= rl

                    if not cancel_move:
                        first_partner_id = next(iter(by_partner.keys()))
                        partner = by_partner[first_partner_id].mapped("partner_id")[:1]
                        total_amount = sum(abs(x.balance) for x in risk_lines if x.balance)

                        if not total_amount:
                            continue

                        vals_move = {
                            "move_type": "entry",
                            "date": origin_line.date_maturity,
                            "journal_id": journal.id,
                            "company_id": company.id,
                            "ref": ref,
                            "is_confirming_cancel_move": True,
                            "line_ids": [
                                (0, 0, {
                                    "name": "Factoring bank debt cancellation",
                                    "account_id": debt_account.id,
                                    "partner_id": partner.id if partner else False,
                                    "debit": total_amount,
                                    "credit": 0.0,
                                }),
                                (0, 0, {
                                    "name": "Factoring risk reclassification",
                                    "account_id": risk_account.id,
                                    "partner_id": partner.id if partner else False,
                                    "debit": 0.0,
                                    "credit": total_amount,
                                }),
                            ],
                        }
                        cancel_move = Move.create(vals_move)

                    for partner_id, partner_risk_lines in by_partner.items():
                        for rl in partner_risk_lines:
                            rl.write({"yostesis_confirming_cancel_move_id": cancel_move.id})

                    invoice_lines = full_rec.reconciled_line_ids.filtered(
                        lambda l: l.account_internal_type in ("receivable", "payable")
                        and l.move_id.move_type in ("out_invoice", "in_invoice", "out_refund", "in_refund")
                        and not l.yostesis_confirming_cancel_move_id
                    )
                    if invoice_lines:
                        invoice_lines.write({"yostesis_confirming_cancel_move_id": cancel_move.id})

                    if not self.env.context.get("confirming_test_only") and cancel_move.state == "draft":
                        cancel_move.action_post()

                    cancel_risk_lines = cancel_move.line_ids.filtered(
                        lambda l: l.account_id.id == risk_account.id
                        and l.company_id.id == company.id
                        and not l.reconciled
                        and not l.full_reconcile_id
                    )

                    for rl in risk_lines:
                        candidates = cancel_risk_lines.filtered(
                            lambda l: (not rl.partner_id) or (l.partner_id.id == rl.partner_id.id)
                        )
                        if not candidates:
                            candidates = cancel_risk_lines
                        if not candidates:
                            continue

                        line_to_match = candidates[:1]
                        to_rec = (rl | line_to_match).filtered(lambda l: not l.reconciled and not l.full_reconcile_id)
                        if len(to_rec) == 2:
                            to_rec.reconcile()

                except Exception as e:
                    MailMessage.create({
                        "model": "account.payment.order",
                        "res_id": order.id,
                        "body": "Error en cron factoring con línea %s: %s" % (payment_line.id, e),
                    })
                    continue
