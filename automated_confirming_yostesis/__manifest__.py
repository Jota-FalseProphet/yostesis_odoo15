# -*- coding: utf-8 -*-
{
    'name': "Automated Confirming Yostesis",

    'summary': "Automatiza la cancelación y conciliación final del confirming (factoring) mediante cron y ajustes en payments.",

    'description': """
        Módulo para automatizar el paso final del confirming / factoring: detecta efectos descontados aplicables, genera asientos de cancelación y realiza conciliaciones automáticamente.

        Comportamiento principal:
        - Añade campos en `account.move` / `account.move.line` para registrar y vincular asientos de cancelación de confirming/factoring.
        - Proporciona un cron (scheduled action) `Confirming auto conciliation` que se puede activar desde `Ajustes → Configuración` y se ejecuta por defecto diariamente (1AM) para procesar órdenes de cobro (`account.payment.order`).
        - El cron busca líneas conciliadas relacionadas con cuentas de riesgo (p.ej. 4311) cuyo vencimiento cumpla las reglas configuradas y crea un `account.move` de tipo contable para cancelar la deuda con el banco (reclasificación riesgo/deuda).
        - El cron utiliza parámetros configurables almacenados en `ir.config_parameter` (mediante `res.config.settings`):
            * `yostesis_confirming.confirming_payment_mode_id` — Modo de cobro que identifica órdenes de cobro de confirming.
            * `yostesis_confirming.confirming_from_date` — Fecha mínima para que el cron procese vencimientos.
            * `yostesis_confirming.confirming_risk_account_id` — Cuenta de riesgo (p.ej. 4311) asociada a factoring.
            * `yostesis_confirming.confirming_debt_account_id` — Cuenta destino para la cancelación (p.ej. 5208).
            * `yostesis_confirming.confirming_journal_id` — Diario utilizado para generar asientos de cancelación.
            * `yostesis_confirming.confirming_enable_cron` — Flag para activar/desactivar el cron.
        - Extiende el widget de pagos en facturas para mostrar "Pagado al Vencimiento" para líneas de confirming y ajusta el informe de factura para mostrar la etiqueta adecuada (idioma/fecha).

        Usos y recomendaciones:
        - Pensado para empresas que gestionan confirming/factoring y necesitan automatizar la creación de asientos de cancelación y conciliaciones con el banco.
        - Probar la funcionalidad en un entorno de test antes de activarla en producción; el cron requiere cuentas y un diario válidos configurados.

        Contributors: Yostesis
    """,
    'license': 'AGPL-3',

    'author': "Yostesis",
    'website': "Yostesis",
    'maintainers': ['Yostesis'],
    'support': 'soporte@yostesis.cloud',

    # Categories can be used to filter modules in modules listing
    # Check https://github.com/odoo/odoo/blob/15.0/odoo/addons/base/data/ir_module_category_data.xml
    # for the full list
    'category': 'Accounting',
    'version': '15.0.1.3.2',

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
    
    'qweb': [
        'automated_confirming_yostesis/views/account_payment_widget.xml',
    ],
    
    'assets': {
        'web.assets_backend': [
            'automated_confirming_yostesis/static/src/xml/account_confirming_payment.xml',
        ],
    },

}
