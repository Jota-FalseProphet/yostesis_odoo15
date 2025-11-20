# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError

class AccountBankingMandate(models.Model):
    _inherit = "account.banking.mandate"

    mandate_for_partner_id = fields.Many2one(
        'res.partner',
        string="Empresa del mandato",
        index=True,
        help="Empresa para la que gestionas este mandato (titular u otra con cuenta compartida). "
             "El partner real del mandato (campo 'Empresa') sigue siendo el titular del banco.",
    )

    applies_to_partner_ids = fields.Many2many(
        'res.partner',
        string="Aplica a",
        compute="_compute_applies_to_partner_ids",
        store=False,
        help="Empresas a las que aplica este mandato por compartir la misma cuenta.",
    )

    @api.depends('partner_bank_id',
             'partner_bank_id.partner_id',
             'partner_bank_id.shared_partner_ids',
             'mandate_for_partner_id')
    def _compute_applies_to_partner_ids(self):
        for rec in self:
            if rec.mandate_for_partner_id:
                rec.applies_to_partner_ids = rec.mandate_for_partner_id
            elif rec.partner_bank_id:
                rec.applies_to_partner_ids = (
                    rec.partner_bank_id.partner_id | rec.partner_bank_id.shared_partner_ids
                )
            else:
                rec.applies_to_partner_ids = self.env['res.partner']

    def _domain_partner_bank_for(self, pid, company_id):
        dom_company = ['|', ('company_id', '=', False), ('company_id', '=', company_id)]
        dom_partner = ['|', ('partner_id', '=', pid), ('shared_partner_ids', 'in', pid)]
        return ['&'] + dom_company + dom_partner

    @api.onchange('partner_bank_id', 'company_id', 'mandate_for_partner_id')
    def _onchange_partner_id(self):
        try:
            res = super()._onchange_partner_id()
        except AttributeError:
            res = {}

        res = res or {}
        res.setdefault('domain', {})

        ctx_pid = self.env.context.get('default_partner_id')
        base_partner_id = self.mandate_for_partner_id.id or ctx_pid or (self.partner_id and self.partner_id.id)
        company_id = (self.company_id and self.company_id.id) or self.env.company.id

        if base_partner_id:
            res['domain']['partner_bank_id'] = self._domain_partner_bank_for(base_partner_id, company_id)

        if self.partner_bank_id:
            candidates = (self.partner_bank_id.partner_id | self.partner_bank_id.shared_partner_ids).ids
            res['domain']['mandate_for_partner_id'] = [('id', 'in', candidates)]

            if self.mandate_for_partner_id and self.mandate_for_partner_id.id not in candidates:
                self.mandate_for_partner_id = False
            if not self.mandate_for_partner_id:
                if ctx_pid and ctx_pid in candidates:
                    self.mandate_for_partner_id = ctx_pid
                else:
                    self.mandate_for_partner_id = self.partner_bank_id.partner_id.id

        return res

    @api.constrains('partner_bank_id', 'mandate_for_partner_id')
    def _check_for_partner_candidate(self):
        for rec in self:
            if rec.partner_bank_id and rec.mandate_for_partner_id:
                candidates = rec.partner_bank_id.partner_id | rec.partner_bank_id.shared_partner_ids
                if rec.mandate_for_partner_id not in candidates:
                    raise ValidationError(
                        "La empresa del mandato debe ser el titular de la cuenta o una empresa con cuenta compartida."
                    )
