from odoo import api, fields, models
from odoo.tools import float_is_zero


class AccountMove(models.Model):
    _inherit = 'account.move'
    #TODO la empresa 2 USA no tiene configuradas tasas de cambios
    multicompany_reporting_currency_id = fields.Many2one(
        'res.currency',
        compute='_compute_multicompany_reporting_currency_id',
        store=True,
        readonly=True,
    )

    multicompany_reporting_currency_rate = fields.Float(
        compute='_compute_multicompany_reporting_currency_rate',
        store=True,
        digits=(12, 6),
    )

    amount_untaxed_reporting_currency = fields.Monetary(
        string='Base imponible Euro',
        currency_field='multicompany_reporting_currency_id',
        compute='_compute_amount_untaxed_reporting_currency',
        store=True,
        readonly=True,
    )

    def _get_multicompany_reporting_currency_id(self):
        param = (
            self.env['ir.config_parameter']
            .sudo()
            .get_param(
                'base_multicompany_reporting_currency.multicompany_reporting_currency'
            )
        )
        return self.env['res.currency'].browse(int(param))

    @api.depends('currency_id')
    def _compute_multicompany_reporting_currency_id(self):
        reporting_currency = self._get_multicompany_reporting_currency_id()
        for rec in self:
            rec.multicompany_reporting_currency_id = reporting_currency

    @api.depends('currency_id', 'date', 'company_id', 'multicompany_reporting_currency_id')
    def _compute_multicompany_reporting_currency_rate(self):
        for rec in self:
            if not rec.company_id:
                rec.multicompany_reporting_currency_rate = (
                    rec.multicompany_reporting_currency_id.with_context(
                        date=rec.date
                    ).rate or 1.0
                )
            elif rec.currency_id and rec.multicompany_reporting_currency_id:
                rec.multicompany_reporting_currency_rate = self.env[
                    'res.currency'
                ]._get_conversion_rate(
                    rec.currency_id,
                    rec.multicompany_reporting_currency_id,
                    rec.company_id,
                    rec.date or fields.Date.today(),
                )
            else:
                rec.multicompany_reporting_currency_rate = 1.0

    financing_bank = fields.Selection(
        [('caixa_popular', 'Caixa Popular')],
        string='Banco financiador',
    )
    financing_maturity_date = fields.Date(
        string='Fecha vencimiento financiación',
    )

    @api.depends(
        'amount_untaxed_signed',
        'amount_untaxed',
        'multicompany_reporting_currency_id',
        'multicompany_reporting_currency_rate',
        'company_currency_id',
    )
    def _compute_amount_untaxed_reporting_currency(self):
        for rec in self:
            reporting = rec.multicompany_reporting_currency_id
            # Si la moneda de la compañía == moneda de reporting,
            # usar amount_untaxed_signed (ya convertido con la tasa del día)
            if rec.company_currency_id == reporting:
                rec.amount_untaxed_reporting_currency = abs(rec.amount_untaxed_signed)
            elif rec.currency_id == reporting:
                rec.amount_untaxed_reporting_currency = rec.amount_untaxed
            elif float_is_zero(
                rec.multicompany_reporting_currency_rate,
                precision_rounding=(
                    rec.currency_id or self.env.company.currency_id
                ).rounding,
            ):
                rec.amount_untaxed_reporting_currency = rec.amount_untaxed
            else:
                rec.amount_untaxed_reporting_currency = (
                    rec.amount_untaxed * rec.multicompany_reporting_currency_rate
                )
