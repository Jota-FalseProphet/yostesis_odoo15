# -*- coding: utf-8 -*-
{
    "name": "Internal Reference Indaws Smasher Yostesis",
    "version": "15.0.1.0.0",
    "summary": "Parche ninja para códigos y rendimiento de productos",
    "description": """
        Al modificar atributos en la ficha Producto:
        * Mata los writes recursivos del default_code
        * Deja de renumerar variantes a lo loco
        * Añade una vista ligera post-spa
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "category": "Accounting",
    "license": "LGPL-3",
    "maintainers": ["Yostesis"],
    "depends": [
        "product",
        "product_variant_default_code",
        "indaws_internal_reference",  
    ],
    "data": [
        "views/product_template_light_form.xml",
    ],
    "application": False,
    "installable": True,
}
