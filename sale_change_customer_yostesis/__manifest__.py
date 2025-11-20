# -*- coding: utf-8 -*-
{
    "name": "Cambiar cliente en pedido confirmado (sin romper MOs)",
    "summary": "Permite cambiar el cliente de un pedido confirmado sin afectar MOs ni entregas ya lanzadas.",
    "version": "15.0.1.0.5",
    "author": "Yostesis",
    "website": "",
    "category": "Sales",
    "license": "LGPL-3",
    "depends": ["sale_management", "stock", "mrp", "account", "mail","puntmobles_custom_permissions_yostesis"],
    "data": [
        "security/ir.model.access.csv",
        "views/change_sale_customer_wizard_views.xml",
        "views/sale_order_views.xml",
    ],
    "installable": True,
    "application": False,
}
