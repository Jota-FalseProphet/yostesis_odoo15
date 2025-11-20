from odoo import models

class AccountVoucherWizardPurchase(models.TransientModel):
    _inherit = "account.voucher.wizard.purchase"

    def _prepare_payment_vals(self, purchase):
        vals = super()._prepare_payment_vals(purchase)
        vals["purchase_id"] = purchase.id
        vals["destination_account_id"] = (purchase.company_id.account_advance_supplier_id or
            self.env["account.account"].search([("code","=like","407%"),("company_id","=",purchase.company_id.id),("deprecated","=",False)],limit=1)
        ).id
        vals["is_advance"] = True
        return vals

