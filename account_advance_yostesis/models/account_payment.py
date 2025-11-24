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

    def action_post(self):
        res = super().action_post()
        self._fix_simple_sale_advance_entries()
        return res

    def _fix_simple_sale_advance_entries(self):
        SaleOrder = self.env["sale.order"]
        for pay in self:
            if not pay.is_advance:
                continue
            if pay.purchase_id:
                continue

            sale = SaleOrder.search(
                [("account_payment_ids", "in", pay.id)],
                limit=1,
            )
            if not sale:
                continue

            move = pay.move_id
            if not move or move.state != "posted":
                continue

            company = move.company_id
            acc_adv = company.account_advance_customer_id
            if not acc_adv:
                continue

            adv_line = move.line_ids.filtered(
                lambda l: l.account_id.id == acc_adv.id
            )[:1]
            if not adv_line:
                continue

            partner = pay.partner_id.commercial_partner_id
            receivable = partner.property_account_receivable_id
            if not receivable:
                continue

            other_lines = move.line_ids - adv_line
            other_lines = other_lines.filtered(
                lambda l: l.account_internal_type not in ("receivable", "payable")
            )
            if len(other_lines) != 1:
                continue

            other_lines.with_context(
                skip_account_move_synchronization=True
            ).write(
                {"account_id": receivable.id}
            )
