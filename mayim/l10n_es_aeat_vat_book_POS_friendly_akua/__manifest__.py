# -*- coding: utf-8 -*-
{
    'name': "Exclude from error POS in VAT Book AEAT - AKUA",

    "version": "15.0.1.0.0",
    "summary": "Compatibiliza el libro IVA AEAT con tickets POS anónimos (evita excepciones de partner/VAT).",
    "description": """
        Este pequeño módulo hace que el módulo `l10n_es_aeat_vat_book` sea más amigo del Punto de Venta (POS) cuando se generan tickets anónimos.

        Qué hace exactamente:
        - Añade el campo booleano `vat_book_pos_anonymous` en `account.journal` para marcar diarios de POS cuyos tickets deben ser tratados como anónimos en el libro de IVA (no generan excepción "Without partner" o "Without VAT").
        - Marca automáticamente el diario vinculado a una configuración POS (`pos.config`) cuando se crea o se cambia el diario.
        - Modifica la comprobación de excepciones del libro de IVA (`l10n.es.vat.book._check_exceptions`) para ignorar las líneas de movimientos contables que provienen de diarios POS marcados como anónimos y que no tienen partner o vat number.

        Beneficio principal:
        - Evita que los tickets del POS (por ejemplo, ventas al contado sin partner o sin NIF) generen excepciones en el Libro de IVA, manteniendo un control más preciso para tickets anónimos.

        Recomendación de uso:
        - Marcar explícitamente los diarios POS que usan tickets anónimos (en Configuración del POS) para que sean ignorados por las comprobaciones de excepciones del libro de IVA.
    """,
    "author": "Productika.Online SL.",
    "website": "https://productika.online",
    "maintainers": ["Juan José (Jota) Perdomo Ortiz"],

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',

    # any module necessary for this one to work correctly
    'depends': [
        'l10n_es_vat_book',
        'akua_pos',
    ],
    # always loaded
    'data': [
        # No views are required; the models add behavior automatically. Keep data section empty.
    ],
    'license': 'LGPL-3',
    'installable': True,
    'application': False,
    'auto_install': False,
    'support': 'soporte@productika.online',

}
