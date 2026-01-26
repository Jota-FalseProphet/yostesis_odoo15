from odoo import models, api

class AccountMove(models.Model):
    _inherit = "account.move"

    @api.onchange('partner_id')
    def _onchange_partner_id_bank_domain(self):
        partner = self.commercial_partner_id or self.partner_id
        if partner:
            domain = ['|', ('partner_id', '=', partner.id), ('shared_partner_ids', 'in', partner.id)]
            return {'domain': {'partner_bank_id': domain}}
        return {}
