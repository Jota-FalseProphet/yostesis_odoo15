from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    is_advance = fields.Boolean(readonly=True, copy=False)

    def _get_counterpart_move_line_vals(self, write_off_line_vals=None):
        self.ensure_one()
        vals = super()._get_counterpart_move_line_vals(write_off_line_vals)
        if self.is_advance and self.company_id.account_advance_customer_id:
            vals["account_id"] = self.company_id.account_advance_customer_id.id
        return vals

    def _get_liquidity_move_line_vals(self, amount):
        self.ensure_one()
        vals = super()._get_liquidity_move_line_vals(amount)

        if not self.is_advance:
            return vals

        company = self.company_id
        suspense = getattr(company, "account_journal_suspense_id", False)

        if not suspense:
            Settings = self.env["res.config.settings"]
            field = Settings._fields.get("account_journal_suspense_id")
            param_name = getattr(field, "config_parameter", False) if field else False
            if param_name:
                icp = self.env["ir.config_parameter"].sudo()
                suspense_id = icp.get_param(param_name)
                if suspense_id:
                    suspense = self.env["account.account"].browse(int(suspense_id))

        if suspense:
            vals["account_id"] = suspense.id

        return vals
