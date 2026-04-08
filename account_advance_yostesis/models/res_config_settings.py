from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    # Cuentas de anticipos
    account_advance_customer_id = fields.Many2one(
        "account.account",
        string="Cuenta anticipos clientes (438)",
        related="company_id.account_advance_customer_id",
        readonly=False,
        help="Cuenta donde se registran los anticipos de clientes. "
             "Normalmente una cuenta 438xxx.",
    )

    account_advance_supplier_id = fields.Many2one(
        "account.account",
        string="Cuenta anticipos proveedores (407)",
        related="company_id.account_advance_supplier_id",
        readonly=False,
        help="Cuenta donde se registran los anticipos a proveedores. "
             "Normalmente una cuenta 407xxx.",
    )

    # Diario para asientos de reversión
    advance_transfer_journal_id = fields.Many2one(
        "account.journal",
        string="Diario de aplicación de anticipos",
        related="company_id.advance_transfer_journal_id",
        readonly=False,
        help="Diario donde se crean los asientos de reversión (438→430 o 407→400) "
             "cuando se aplican anticipos a facturas.",
    )
