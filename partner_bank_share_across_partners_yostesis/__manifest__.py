# -*- coding: utf-8 -*-
{
    "name": "Partner Bank: allow same account across partners",
    "summary": "Permite reutilizar el mismo número de cuenta bancaria en distintos partners.",
    "version": "15.0.1.2.11",
    "author": "Yostesis",
    "website": "https://yostesis.com",
    "license": "LGPL-3",
    "category": "Accounting",
    "depends": ["account", 
                "account_banking_mandate", 
                "account_sepa_direct_debit"],
    "data": [
        "views/res_partner_view.xml",
        "views/account_banking_mandate_view.xml"
        # "views/account_move_view.xml",
    ],
    "installable": True,
    "application": False,
}