from odoo import models, fields


class AccountJournal(models.Model):
    _inherit = "account.journal"

    confirming_payment_account_id = fields.Many2one(
        "account.account",
        string="Cuenta Confirming Proveedores",
        domain="[('company_id', '=', company_id), ('deprecated', '=', False)]",
        help=(
            "Cuenta que se usará como cuenta de liquidez en las órdenes de pago "
            "de Confirming a proveedores. "
            "Si se deja vacío, se usará la cuenta estándar de pagos pendientes "
            "del método de pago."
        ),
    )
