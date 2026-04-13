from odoo import SUPERUSER_ID, api


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    # sale.order: recalcular amount_untaxed_reporting_currency
    orders = env['sale.order'].search([('amount_untaxed', '>', 0)])
    orders._compute_amount_untaxed_reporting_currency()

    # account.move: usar amount_untaxed_signed como fuente de verdad
    # (ya tiene la tasa de cambio del día de la factura)
    cr.execute("""
        SELECT id FROM ir_config_parameter
        WHERE key = 'base_multicompany_reporting_currency.multicompany_reporting_currency'
    """)
    row = cr.fetchone()
    if not row:
        return

    moves = env['account.move'].search([('amount_untaxed', '>', 0)])
    moves._compute_multicompany_reporting_currency_id()

    # Derivar tasa real y amount desde amount_untaxed_signed
    cr.execute("""
        UPDATE account_move am
        SET multicompany_reporting_currency_rate =
                CASE
                    WHEN am.amount_untaxed = 0 THEN 1.0
                    ELSE ABS(am.amount_untaxed_signed) / am.amount_untaxed
                END,
            amount_untaxed_reporting_currency = ABS(am.amount_untaxed_signed)
        FROM res_company rc
        WHERE rc.id = am.company_id
          AND am.amount_untaxed > 0
          AND rc.currency_id = am.multicompany_reporting_currency_id
    """)
