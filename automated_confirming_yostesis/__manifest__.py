# -*- coding: utf-8 -*-
{
    'name': "Automated Confirming Yostesis",

    'summary': "Module created to automate confirming final step conciliation. ",

    'description': """
        Module that automates confirming final step conciliation. Using scheduled actions that runs every day at 1AM
        checking payment terms of invoices in confirmed state, that also uses the Payment Mode with the 'Confirming' check previously marked.

        Do not contact contributors directly about support or help with technical issues.

        Contributors:

        --  Yostesis
        --  Yostesis
    """,

    'author': "Yostesis",
    'website': "Yostesis",
    'maintainers': ['Yostesis'],
    'support': 'soporte@yostesis.cloud',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '15.0.1.2.31',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'account_payment_mode',
        'account_payment_order',
        'l10n_es_payment_order_confirming_aef',
    ],
    # always loaded
    'data': [
        'data/confirming_cron.xml',
        'views/res_config_settings_views.xml',
        'reports/report_invoice_confirming.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'automated_confirming_yostesis/static/src/xml/account_confirming_payment.xml',
        ],
    },

}
