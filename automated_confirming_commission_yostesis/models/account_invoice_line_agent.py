from odoo import models


class AccountInvoiceLineAgent(models.Model):
    _inherit = "account.invoice.line.agent"

    def _skip_settlement(self):
        res = super()._skip_settlement()
        if res:
            return res

        invoice = self.invoice_id
        if not invoice:
            return res

        if invoice.payment_state != "in_payment":
            return res

        if invoice.confirming_cancel_move_id:
            return res

        icp = self.env["ir.config_parameter"].sudo()
        risk_account_param = icp.get_param("yostesis_confirming.confirming_risk_account_id")
        if not risk_account_param:
            return res

        risk_account_id = int(risk_account_param)

        recv_pay_lines = invoice.line_ids.filtered(
            lambda l: l.account_internal_type in ("receivable", "payable")
        )
        if not recv_pay_lines:
            return res

        full_recs = recv_pay_lines.mapped("full_reconcile_id")
        if not full_recs:
            return res

        related_moves = full_recs.mapped("reconciled_line_ids.move_id")
        risk_lines = related_moves.mapped("line_ids").filtered(
            lambda l: l.account_id.id == risk_account_id
            and not l.yostesis_confirming_cancel_move_id
            and not l.reconciled
        )

        if risk_lines:
            return True

        return res
