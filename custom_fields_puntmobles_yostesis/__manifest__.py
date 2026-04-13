# -*- coding: utf-8 -*-
{
    "name": "Custom Fields for Puntmobles by Yostesis",
    "version": "15.0.1.8.9",
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
        "account_payment_order",
        "purchase_stock",
        "stock_picking_batch",
        "puntmobles_custom_permissions_yostesis",
        "sale_multicompany_reporting_currency",
        ],
    "data": [
        "security/ir.model.access.csv",
        "views/mrp_views.xml",
        "views/account_move_views.xml",
        "views/account_move_line_views.xml",
        "views/res_company_views.xml",
        "views/mrp_workorder_views.xml",
        "views/sale_views.xml",
        "views/sale_order_views.xml",
        "views/stock_picking_views.xml",
        "views/crm_claim_views.xml",
        "views/sale_order_project_views.xml",
        "views/account_payment_order_views.xml",
        "report/report_sale_obs.xml",
        "report/report_mrp_obs.xml",
        "report/report_picking_multiples.xml",
        "report/report_picking_multiples_action.xml",
    ],
    
    #Este modulo es una guarrada, lo siento Ignacio
    "post_init_hook": "_post_init_copy_commitment_to_prevista",
    "application": False,
    "installable": True,
}
