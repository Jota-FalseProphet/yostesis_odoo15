# pos_scale_akua/__manifest__.py
{
    "name": "POS Scale Integration (Akua)",
    "version": "15.0.1.0.0",
    "author": "Jota",
    "website": "",
    "category": "Point of Sale",
    "license": "LGPL-3",
    "depends": ["point_of_sale"],
    "data": [],
    "assets": {
        "point_of_sale.assets": [
            "pos_scale_akua/static/src/js/scale_button.js",
            "pos_scale_akua/static/src/xml/scale_button.xml",
        ],
    },
    "installable": True,
    "application": False,
}
