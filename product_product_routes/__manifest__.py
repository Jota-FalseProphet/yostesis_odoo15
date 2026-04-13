# Copyright 2024 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

{
    "name": "Product Variant Routes",
    "summary": """
        This module allow us to choose different routes for variants.
        """,
    "version": "15.0.1.0.1",
    "category": "Warehouse",
    "website": "https://sodexis.com/",
    "author": "Sodexis",
    "license": "OPL-1",
    "installable": True,
    "application": False,
    "images": ["images/main_screenshot.jpg"],
    "depends": [
        "stock",
    ],
    "data": [],
    "post_init_hook": "post_init_hook",
    "price": "9.99",
    "currency": "USD",
}
