{
    'name': "Yostesis - Plantillas de correo personalizadas",
    'version': '15.0.1.0.0',
    'author': "Yostesis",
    'website': "https://yostesis.com",
    'category': 'Customizations',
    'license': 'LGPL-3',
    'summary': "Plantillas de correo de Punt Mobles para uso comercial (sale.order)",
    'depends': ['sale'],
    'data': [
        'data/mail_templates.xml',
    ],
    'post_init_hook': 'post_init_hook',
    'installable': True,
    'application': False,
    'auto_install': False,
}
