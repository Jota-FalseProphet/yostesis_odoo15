from odoo import fields, models


class AccountJournal(models.Model):
    _inherit = "account.journal"

    vat_book_pos_anonymous = fields.Boolean(
        string="POS anonymous VAT book"
    )
