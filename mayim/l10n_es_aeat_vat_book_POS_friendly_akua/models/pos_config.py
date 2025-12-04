from odoo import models


class PosConfig(models.Model):
    _inherit = "pos.config"

    def _mark_pos_vat_book_journal(self):
        for pos in self:
            if pos.journal_id:
                pos.journal_id.vat_book_pos_anonymous = True

    def create(self, vals_list):
        records = super().create(vals_list)
        records._mark_pos_vat_book_journal()
        return records

    def write(self, vals):
        res = super().write(vals)
        if "journal_id" in vals:
            self._mark_pos_vat_book_journal()
        return res
    
    
