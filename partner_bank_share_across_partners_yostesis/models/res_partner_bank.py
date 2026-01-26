# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api


class ResPartnerBank(models.Model):
    _inherit = "res.partner.bank"

    shared_partner_ids = fields.Many2many(
        comodel_name="res.partner",
        relation="res_partner_bank_shared_rel",
        column1="bank_id",
        column2="partner_id",
        string="Compartida con",
        help="Partners adicionales que pueden usar esta cuenta bancaria."
    )

    @api.model
    def _sanitize_acc_shared(self, number):
        return re.sub(r'[^0-9A-Za-z]', '', (number or '')).upper()

    @api.model_create_multi
    def create(self, vals_list):
        result_records = []
        to_create = []

        to_create_indexes = []

        for idx, vals in enumerate(vals_list):
            acc = vals.get('acc_number') or vals.get('sanitized_acc_number')
            partner_id = vals.get('partner_id')
            company_id = vals.get('company_id') or self.env.company.id

            if acc:
                sanitized = self._sanitize_acc_shared(acc)
                existing = self.search([
                    ('sanitized_acc_number', '=', sanitized),
                    '|', ('company_id', '=', False), ('company_id', '=', company_id),
                ], limit=1)

                if existing:
                    if partner_id and partner_id not in existing.shared_partner_ids.ids:
                        existing.write({'shared_partner_ids': [(4, partner_id)]})
                    result_records.append(existing)
                    continue

            to_create.append(vals)
            to_create_indexes.append(len(result_records))
            result_records.append(self.browse())

        if to_create:
            created_batch = super(ResPartnerBank, self).create(to_create)
            for pos, rec in zip(to_create_indexes, created_batch):
                result_records[pos] = rec

        return sum(result_records, self.browse())


class ResPartner(models.Model):
    _inherit = "res.partner"

    shared_bank_ids = fields.Many2many(
        comodel_name="res.partner.bank",
        relation="res_partner_bank_shared_rel",
        column1="partner_id",
        column2="bank_id",
        string="Cuentas bancarias compartidas",
        help="Cuentas bancarias de otros contactos que este partner puede usar."
    )
