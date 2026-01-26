from odoo import fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # flag invisible: sólo lo pone el wizard
    is_advance = fields.Boolean(readonly=True)

    def _get_counterpart_move_line_vals(self, write_off_line_vals=None):
        vals = super()._get_counterpart_move_line_vals(write_off_line_vals)
        if (
            self.is_advance
            and self.company_id.account_advance_customer_id
        ):
            vals["account_id"] = self.company_id.account_advance_customer_id.id
        return vals
