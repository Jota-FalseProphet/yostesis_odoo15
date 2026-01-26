# -*- coding: utf-8 -*-
{
    "name": "Customer Advance Account (438) - yostesis",
    "version": "15.0.1.0.0",
    "summary": "Usa la cuenta 438 para anticipos de clientes",
    "description": """
        Asigna automáticamente la cuenta **438** (Anticipos de clientes) en los cobros marcados como anticipo, manteniendo intacta la 430.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "category": "Accounting",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "sale_advance_payment",
        ],
    "data": [
        "views/res_company_view.xml",
        # "views/account_payment_view.xml",
    ],
    "application": False,
    "installable": True,
}
