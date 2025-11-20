from odoo import models, api

class AccountInvoiceLineAgent(models.Model):
    _inherit = 'account.invoice.line.agent'

    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]
        valid_vals = []
        for vals in vals_list:
            if vals.get('object_id'):
                valid_vals.append(vals)
        if not valid_vals:
            return self.browse()
        return super(AccountInvoiceLineAgent, self).create(valid_vals)
