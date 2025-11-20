# -*- coding: utf-8 -*-
{
    "name": "INDAWS FIXES: Yostesis Patches",
    "version": "15.0.1.5.6",
    "summary": "A summary of mini patches for Indaws modules",
    "description": """
        This is a collection of small patches to fix issues in Indaws modules.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "maintainers": ["Yostesis"],
    "depends": [
        "web_studio",
        "mrp",
        "sale_mrp",
        "product_variant_default_code",

        "indaws_internal_reference",
        ],
    "data": [
        "views/sale_report_fix.xml",
    ],
    "application": False,
    "installable": True,
}
