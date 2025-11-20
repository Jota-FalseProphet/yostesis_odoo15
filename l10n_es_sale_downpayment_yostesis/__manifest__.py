# -*- coding: utf-8 -*-
{
    "name": "ES Down Payments to 438 ('Anticipos de clientes') by Yostesis",
    "version": "15.0.1.10.5",
    "summary": "A soft rework of downpayment method for l10n_es",
    "description": """Uses the 438 account for down payments in sales invoices, as required by Spanish accounting standards.""",
    "author": "Yostesis",
    "website": "https://yostesis.com",
    "category": "Accounting",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "sale_management",
        "l10n_es",
    ],

    'data': [
        'reports/report_invoice_with_payments.xml',
        'reports/report_invoice_hide_qty_discounts.xml',
    ],
   
    "application": False,
    "installable": True,
}
