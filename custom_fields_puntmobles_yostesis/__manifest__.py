# -*- coding: utf-8 -*-
{
    "name": "Custom Fields for Puntmobles by Yostesis",
    "version": "15.0.1.7.3",
    "summary": "A bunch for custom fields needed by PuntMobles",
    "description": """
        This is a collection of custom fields required by PuntMobles for their Odoo implementation.
        It includes fields for various models to enhance functionality and meet specific business needs.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "maintainers": ["Yostesis"],
    "depends": [
        "sale", 
        "sale_stock",
        "mrp",
        "sale_mrp",
        "indaws_sale_report_customization",
        ],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_views.xml",
        "views/mrp_workorder_views.xml",
        "views/sale_views.xml",
        "views/stock_picking_views.xml",
        "views/crm_claim_views.xml",
        "views/sale_order_project_views.xml",
        "report/report_sale_obs.xml",
        "report/report_mrp_obs.xml",


    ],
    "application": False,
    "installable": True,
}
