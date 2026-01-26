# -*- coding: utf-8 -*-
{
    'name': "Selectable account for confirming in journals",

    'summary': "Module created to select account for confirming in journals. ",

    'description': """
        Module that allows selecting the account for confirming in journals. Also allows configuring a payment mode for confirming it from settings. 

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
    'version': '15.0.1.2.0',

    # any module necessary for this one to work correctly
    'depends': [
        'account',
        'account_payment_mode',
        'account_payment_order',
        'automated_confirming_yostesis',
    ],
    # always loaded
    'data': [
        'views/account_journal_views.xml',
        'views/res_config_settings_views.xml',
    ],

}
