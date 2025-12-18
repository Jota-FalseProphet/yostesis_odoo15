# -*- coding: utf-8 -*-
{
    "name": "ES Down Payments to 438 ('Anticipos de clientes') by Yostesis",
    "version": "15.0.1.11.2",
    "summary": "Gestión de downpayments con cuenta 438 (anticipos de clientes) - NO compatible con advance payment",
    "description": """
        Módulo que implementa downpayments (pagos anticipados) en Odoo usando la cuenta 438 (Anticipos de clientes) según normativas contables españolas.

        Funcionalidades principales:

        - Detecta automáticamente facturas de downpayment (por sale.order.line.is_downpayment o etiqueta en nombre).
        - Recomputa líneas de pago usando la cuenta 438 como destino de anticipos en lugar del receptor estándar.
        - Permite registrar múltiples downpayments sobre un mismo pedido y factura.
        - Genera notas con referencia y fecha de pago del anticipio en la factura.
        - Incluye un wizard de pago anticipado (`account.payment.register`) especializado en flujos 438.
        - Valida y advierte contra mezcla de downpayment con advance payment simple (módulo account_advance_yostesis).

        Compatibilidad y limitaciones:

        - ADVERTENCIA: Este módulo NO es compatible con el módulo advance_payment simple (account_advance_yostesis).
        - Si un pedido tiene anticipos simples disponibles (advance payment), el downpayment será bloqueado para evitar mezcla de flujos.
        - Use downpayment si quiere control granular sobre cada anticipo en 438 (fecha, referencia, conciliación).
        - Use advance payment si prefiere anticipo automático aplicado en factura.

        Reportes especializados:
        - Factura con detalles de pagos anticipados (438).
        - Ocultación de cantidades negativas y descuentos para downpayments.

        Dependencias: account, sale_management, l10n_es.
    """,
    "author": "Yostesis",
    "website": "https://yostesis.com",
    "category": "Accounting",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "sale_management",
        "l10n_es",
        "account_advance_yostesis",
    ],

    'data': [
        'views/sale_advance_payment_inv_views.xml',
        'reports/report_invoice_with_payments.xml',
        'reports/report_invoice_hide_qty_discounts.xml',
    ],
   
    "application": False,
    "installable": True,
}
