# -*- coding: utf-8 -*-
{
    'name': "Stock Packing List Custom PDF Yostesis",

    'summary': "Module created to modify the stock packing list PDF report",

    'description': """
        Module for changing various aspects of the stock packing list PDF report,
        as the weight system, fields showed in spanish and the volumen showed in cubic meters.

        Do not contact contributors directly about support or help with technical issues.

        Contributors:

        --  Yostesis
        --  Yostesis
    """,

    "version": "15.0.5.4.0",
    "author": "Yostesis",
    "website": "https://yostesis.cloud",
    "maintainers": ["Yostesis"],
    "support": "soporte@yostesis.cloud",
    "category": "Inventory",
    "license": "LGPL-3",
    "depends": ["stock", 
                "indaws_custom_reports",],
    "data": [
        "views/report_picking_patch.xml",
    ],
    "installable": True,
    "auto_install": False,
}