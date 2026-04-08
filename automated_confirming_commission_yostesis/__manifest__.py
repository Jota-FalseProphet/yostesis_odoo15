# -*- coding: utf-8 -*-
{
    'name': "Automated Confirming - Commission Compatibility",
    'summary': "Evita liquidar comisiones en facturas de factoring que están 'en proceso de pago' pero sin vencer.",
    'description': """
        Módulo puente entre automated_confirming_yostesis y account_commission.

        Problema que resuelve:
        - Las facturas en factoring pasan a estado 'in_payment' cuando se incluyen en una remesa.
        - El módulo de comisiones considera 'in_payment' como válido para liquidar comisiones.
        - Pero en factoring, 'in_payment' significa que el banco aún no ha cobrado (hay riesgo en 4311).
        - Las comisiones no deberían liquidarse hasta que el banco confirme el cobro al vencimiento.

        Solución:
        - Extiende el método _skip_settlement() de account.invoice.line.agent.
        - Si la factura está en factoring (tiene líneas de riesgo 4311) y está 'in_payment',
          pero NO tiene asiento de cancelación de confirming, se salta la liquidación.
        - Una vez el cron de factoring crea el asiento de cancelación, la factura pasa a 'paid'
          y las comisiones se pueden liquidar normalmente.
    """,
    'license': 'AGPL-3',
    'author': "Yostesis",
    'website': "Yostesis",
    'maintainers': ['Yostesis'],
    'category': 'Accounting',
    'version': '15.0.1.0.0',
    'depends': [
        'automated_confirming_yostesis',
        'account_commission',
    ],
    'data': [],
    'auto_install': True,
    'application': False,
    'installable': True,
}
