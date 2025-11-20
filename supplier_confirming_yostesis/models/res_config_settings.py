from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    confirming_supplier_payment_mode_id = fields.Many2one(
        "account.payment.mode",
        string="Modo de pago Confirming Proveedores",
        config_parameter="yostesis_confirming.confirming_supplier_payment_mode_id",
    )
