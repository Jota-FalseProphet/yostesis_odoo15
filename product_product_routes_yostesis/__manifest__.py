{
    "name": "Product Variant Routes - Template Control",
    "summary": "Permite decidir si las rutas se gestionan desde la plantilla o desde las variantes.",
    "description": """
        Extiende el módulo product_product_routes para añadir un checkbox
        "Gestionar rutas desde las variantes" en la plantilla de producto.

        - Check marcado: las rutas se gestionan individualmente en cada variante (comportamiento product_product_routes).
        - Check desmarcado: las rutas de la plantilla se propagan a todas las variantes automáticamente.
    """,
    "license": "AGPL-3",
    "author": "Yostesis",
    "website": "https://yostesis.cloud",
    "category": "Warehouse",
    "version": "15.0.1.0.4",
    "depends": [
        "product_product_routes",
    ],
    "data": [
        "views/product_template_views.xml",
        "views/product_product_views.xml",
    ],
    "installable": True,
    "auto_install": False,
}
