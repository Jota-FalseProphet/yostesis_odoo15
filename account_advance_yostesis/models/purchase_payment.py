from odoo import models
from odoo.exceptions import UserError


class AccountPayment(models.Model):
    _inherit = "account.payment"

    def _get_407_account(self):
        self.ensure_one()
        account = self.company_id.account_advance_supplier_id
        if not account:
            account = self.env["account.account"].search(
                [
                    ("company_id", "=", self.company_id.id),
                    ("code", "=like", "407%"),
                    ("reconcile", "=", True),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )
        if not account:
            raise UserError(
                "No se encontró la cuenta 407 (Anticipos a proveedores). "
                "Configúrala en la compañía o crea una cuenta 407 conciliable."
            )
        return account

    def _get_destination_account_id(self):
        self.ensure_one()
        if (
            self.purchase_id
            and self.partner_type == "supplier"
            and self.payment_type == "outbound"
        ):
            return self._get_407_account().id
        return super()._get_destination_account_id()

    def _get_counterpart_move_line_vals(self, write_off_line_vals=None):
        vals = super()._get_counterpart_move_line_vals(write_off_line_vals)
        if (
            self.purchase_id
            and self.partner_type == "supplier"
            and self.payment_type == "outbound"
        ):
            vals["account_id"] = self._get_407_account().id
        return vals

    def _get_liquidity_move_line_vals(self, amount):
        vals = super()._get_liquidity_move_line_vals(amount)
        if (
            self.purchase_id
            and self.partner_type == "supplier"
            and self.payment_type == "outbound"
        ):
            suspense = self.company_id.account_journal_suspense_account_id
            if suspense:
                vals["account_id"] = suspense.id
        return vals
