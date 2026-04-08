{
    "name": "Product Purchase Collection (Colección Compra)",
    "version": "15.0.2.0.0",
    "summary": "Adds a Purchase Collection field to product templates",
    "author": "Yostesis",
    "website": "Yostesis",
    "maintainers": ["Yostesis"],
    "depends": ["product", "puntmobles_custom_permissions_yostesis"],
    "data": [
        "security/ir.model.access.csv",
        "views/product_template_views.xml",
        "views/res_users_views.xml",
    ],
    "post_init_hook": "_post_init_load_purchase_collections",
    "application": False,
    "installable": True,
}
