# -*- coding: utf-8 -*-
{
    "name": "Customer/Supplier customized advance account (438/407) - Yostesis",
    "version": "15.0.4.4.5",
    "summary": "Usa la cuenta 438 para anticipos de clientes y la 407 para anticipos de proveedores.",
    "description": """
        Asigna automáticamente la cuenta **438** (Anticipos de clientes) en los cobros marcados como anticipo, manteniendo intacta la 430.
        Igualmente asigna la cuenta **407** (Anticipos de proveedores) en los pagos marcados como anticipo, manteniendo intacta la 400.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "category": "Accounting",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "sale_advance_payment",
        "purchase_advance_payment",
        ],
    "data": [
        "views/res_company_view.xml",
        "views/sale_order_view.xml",
        "report/report_invoice_advance_totals.xml",
    ],
    "application": False,
    "installable": True,
}
