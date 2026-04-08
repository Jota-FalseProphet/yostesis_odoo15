from odoo import fields, models


class AccountPaymentOrder(models.Model):
    _inherit = "account.payment.order"

    custom_confirmation_date = fields.Date(
        string="Fecha Vto. Confir/Tranf",
    )
