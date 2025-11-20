# -*- coding: utf-8 -*-
{
    'name': "Auto Publish SII Yostesis",

    'summary': "Module created to group all AEAT modification on Akua",

    'description': """
        Module that Auto publishes SII data to AEAT

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
    'version': '15.0.3.6',

    # any module necessary for this one to work correctly
    'depends': ['base',
                'account',
                'l10n_es_aeat_sii_oca',
                'l10n_es_aeat',
                'l10n_es_aeat_sii_match',
                'l10n_es_toponyms',
                'website',],

    # always loaded
    'pre_init_hook': 'pre_init_sii_company',
    'data': [
        'data/cron.xml',
        'views/res_company.xml',
        'views/account_move.xml',
        # 'data/aeat_sii_map_data.xml',
    ],

}
