# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class AccountVoucherWizard(models.TransientModel):
    _inherit = "account.voucher.wizard"

    def _prepare_payment_vals(self, sale):
        vals = super()._prepare_payment_vals(sale)
        company = sale.company_id

        account_438 = getattr(company, "account_advance_customer_id", False)

        if not account_438:
            account_438 = self.env["account.account"].search([
                ("code", "=like", "4383%"),
                ("company_id", "=", company.id),
                ("deprecated", "=", False),
            ], limit=1)

        if not account_438:
            account_438 = self.env["account.account"].search([
                ("code", "=like", "438%"),
                ("company_id", "=", company.id),
                ("deprecated", "=", False),
            ], limit=1)

        if not account_438:
            raise UserError(_(
                "No se encontró una cuenta 438/4383 activa en la compañía '%s'. "
                "Configúrala en Compañía o crea una cuenta 4383/438 en el plan contable."
            ) % company.display_name)

        vals["destination_account_id"] = account_438.id
        vals["is_advance"] = True
        return vals


class AccountVoucherWizardPurchase(models.TransientModel):
    _inherit = "account.voucher.wizard.purchase"

    def _prepare_payment_vals(self, purchase):
        vals = super()._prepare_payment_vals(purchase)
        company = purchase.company_id

        account_407 = getattr(company, "account_advance_supplier_id", False)

        if not account_407:
            account_407 = self.env["account.account"].search([
                ("code", "=like", "407%"),
                ("company_id", "=", company.id),
                ("deprecated", "=", False),
                # ("reconcile", "=", True),
            ], limit=1)

        if not account_407:
            raise UserError(_(
                "No se encontró una cuenta 407 activa en la compañía '%s'. "
                "Configúrala en Compañía o crea una cuenta 407 en el plan contable."
            ) % company.display_name)

        vals["destination_account_id"] = account_407.id
        vals["is_advance"] = True
        vals["purchase_id"] = purchase.id
        return vals
