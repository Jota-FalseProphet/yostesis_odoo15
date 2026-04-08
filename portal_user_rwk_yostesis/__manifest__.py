{
    'name': 'Portal Purchase Receipt Date',
    'version': '15.0.1.0.1',
    'category': 'Purchase',
    'summary': 'Shows the Receipt Date field in portal purchase order list',
    'description': '''
Adds the Receipt Date (date_planned) column to the portal purchase orders list view.
This helps portal users see when they can expect to receive items from their orders.
    ''',
    'author': 'Yostesis',
    'website': 'Yostesis',
    'maintainers': ['Yostesis'],
    'support': 'soporte@yostesis.cloud',
    'license': 'LGPL-3',
    'depends': ['purchase'],
    'data': [
        'views/portal_templates.xml',
    ],
    'installable': True,
    'application': False,
}
