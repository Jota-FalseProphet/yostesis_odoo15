from odoo import models


class PaymentReturn(models.Model):
    _inherit = "payment.return"

    def _is_all_factoring(self):
        self.ensure_one()
        icp = self.env["ir.config_parameter"].sudo()
        risk_account_id = int(
            icp.get_param("yostesis_confirming.confirming_risk_account_id") or 0
        )
        if not risk_account_id:
            return False
        return self.line_ids and all(
            any(
                l.account_id.id == risk_account_id
                for l in rl.move_line_ids.mapped("move_id.line_ids")
            )
            for rl in self.line_ids
        )

    def _prepare_move_line(self, move, total_amount):
        vals = super()._prepare_move_line(move, total_amount)
        if self._is_all_factoring():
            suspense_account = self.journal_id.suspense_account_id
            if suspense_account:
                vals["account_id"] = suspense_account.id
                expense_total = sum(self.line_ids.mapped("expense_amount"))
                if expense_total:
                    vals["credit"] += expense_total
            partner = self.line_ids.mapped("partner_id")[:1]
            if partner:
                vals["partner_id"] = partner.id
        return vals


class PaymentReturnLine(models.Model):
    _inherit = "payment.return.line"

    def _prepare_expense_lines_vals(self, move):
        vals_list = super()._prepare_expense_lines_vals(move)
        if self.return_id._is_all_factoring():
            return [v for v in vals_list if v.get("debit")]
        return vals_list
