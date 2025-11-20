from odoo import models, fields, api
from odoo.exceptions import UserError


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    confirming_payment_mode_id = fields.Many2one(
        "account.payment.mode",
        string="Modo de cobro Factoring",
        config_parameter="yostesis_confirming.confirming_payment_mode_id",
    )

    confirming_from_date = fields.Date(
        string="Fecha de inicio para automatizar Factoring",
        help="El cron sólo procesará facturas con fecha de vencimiento igual o posterior a esta.",
    )
    #deuda riesgo que es en verdad de deuda
    confirming_risk_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de deuda Factoring (4311)",
        config_parameter="yostesis_confirming.confirming_risk_account_id",
    )
    #cuenta de deuda que es en verdad de riesgo
    confirming_debt_account_id = fields.Many2one(
        "account.account",
        string="Cuenta de riesgo Factoring (5208)",
        config_parameter="yostesis_confirming.confirming_debt_account_id",
    )

    confirming_journal_id = fields.Many2one(
        "account.journal",
        string="Diario de cancelación",
        config_parameter="yostesis_confirming.confirming_journal_id",
    )

    confirming_enable_cron = fields.Boolean(
        string="Activar cron de Factoring",
        help="Si está activo, el cron procesará automáticamente las órdenes de cobro.",
        config_parameter="yostesis_confirming.confirming_enable_cron",
    )

    @api.onchange("confirming_payment_mode_id")
    def _onchange_confirming_payment_mode(self):
        if not self.confirming_payment_mode_id:
            self.confirming_enable_cron = False
            return {
                "warning": {
                    "title": "Modo de cobro requerido",
                    "message": "Debes seleccionar un modo de cobro antes de poder activar el cron.",
                }
            }

    @api.onchange("confirming_enable_cron")
    def _onchange_confirming_enable_cron(self):
        if self.confirming_enable_cron and not self.confirming_payment_mode_id:
            self.confirming_enable_cron = False
            return {
                "warning": {
                    "title": "Modo de pago requerido",
                    "message": "No puedes activar el cron si no has seleccionado un modo de pago.",
                }
            }

    @api.model
    def get_values(self):
        res = super().get_values()
        icp = self.env["ir.config_parameter"].sudo()
        from_date = icp.get_param("yostesis_confirming.confirming_from_date") or False
        res.update(confirming_from_date=from_date)
        return res

    def set_values(self):
        super().set_values()
        icp = self.env["ir.config_parameter"].sudo()
        icp.set_param(
            "yostesis_confirming.confirming_from_date",
            self.confirming_from_date or "",
        )
