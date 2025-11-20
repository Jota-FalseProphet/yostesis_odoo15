# -*- coding: utf-8 -*-
from odoo import models

class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    def _compute_available_partner_bank_ids(self):
        try:
            super(AccountPaymentRegister, self)._compute_available_partner_bank_ids()
        except AttributeError:
            for rec in self:
                rec.available_partner_bank_ids = False

        for rec in self:
            partner = rec.partner_id.commercial_partner_id if rec.partner_id else False
            if not partner:
                continue

            company = rec.company_id or rec.journal_id.company_id or self.env.company

            shared = self.env['res.partner.bank'].search([
                ('shared_partner_ids', 'in', partner.id),
                '|', ('company_id', '=', False), ('company_id', '=', company.id),
            ])

            if shared:
                rec.available_partner_bank_ids = (rec.available_partner_bank_ids | shared)
                if hasattr(rec, 'show_partner_bank_account') and not rec.show_partner_bank_account:
                    rec.show_partner_bank_account = True
