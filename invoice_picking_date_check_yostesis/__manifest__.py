# -*- coding: utf-8 -*-
{
    "name": "Validación Fechas Albarán-Factura",
    "version": "15.0.1.0",
    "summary": "Avisa al confirmar facturas de proveedor si la fecha de recepción difiere del mes contable",
    "description": """
        Al confirmar una factura de proveedor, verifica que la fecha efectiva de los
        albaranes vinculados esté en el mismo mes/año que la fecha contable de la factura.
        Si hay discrepancia, muestra un wizard con los productos afectados.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "purchase_stock",
    ],
    "data": [
        "security/ir.model.access.csv",
        "views/date_mismatch_wizard_view.xml",
        "views/account_move_views.xml",
    ],
    "application": False,
    "installable": True,
}
