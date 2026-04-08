# -*- coding: utf-8 -*-
{
    "name": "Customer/Supplier customized advance account (438/407) - Yostesis",
    "version": "15.0.4.7.6",
    "summary": "Gestión de anticipos: cuenta 438 para clientes y 407 para proveedores; aplicación y conciliación automática.",
    "description": """
        Módulo para mejorar la gestión de anticipos en Odoo (clientes y proveedores).

        Principales funcionalidades:
        - Utiliza la cuenta 438xxxx para registrar anticipos de clientes (cobros marcados como anticipo), y la cuenta 407xxxx para anticipos de proveedores (pagos marcados como anticipo).
        - Mantiene intactas las cuentas por defecto (430/400) y, cuando procede, crea movimientos puente que aplican y concilian anticipos con facturas automáticamente.
        - Añade campos configurables a la compañía para especificar la cuenta de anticipos de clientes (`account_advance_customer_id`), la cuenta de anticipos a proveedores (`account_advance_supplier_id`) y el diario para traspasos (`advance_transfer_journal_id`).
        - Mejora el comportamiento de `account.payment` para marcar y registrar anticipos correctamente (cuentas contrapartida y de liquidez preferente — 572002000 si está disponible — o fallbacks a suspense configurado).
        - Ajustes específicos y campos nuevos en `sale.order` para mostrar y calcular anticipos:
            * `advance_amount_paid_order` — total de anticipos asociados al pedido (moneda del pedido).
            * `advance_amount_paid_applied` — anticipos ya aplicados en facturas.
            * `advance_amount_paid_available` — anticipos todavía disponibles para el pedido.
            * `commercial_balance_after_advances` — saldo comercial del pedido descontando anticipos.
            * `advance_amount_partner_global` — anticipos globales no conciliados del partner.
        - Fixes y mejoras en asistentes/wizards y pagos:
            * `account.voucher.wizard` y `account.voucher.wizard.purchase` — preparan valores para generar pagos de anticipo con `is_advance=True` y la cuenta destino adecuada (438/407).
            * `sale_advance_close_fix` — sanea la respuesta de `make_advance_payment` para evitar context/params injectado por módulos que puede causar warnings en controladores web.
            * Cambios en `account.payment` para marcar `is_advance` y forzar cuentas destino/contrapartida (438 para ventas, 407 para compras), y usar la cuenta 572002000 o el suspense del diario como cuenta de liquidez preferente.
        - Lógica de `account.move` y conciliación automática:
            * Al postear facturas (cliente/proveedor) intenta aplicar anticipos vinculados al pedido/compra creando movimientos puente (438→430 para clientes, 407→400 para proveedores) y reconcilia automáticamente las líneas implicadas.
            * Método auxiliar `_get_advance_applied_amount` para calcular cuánto anticipo ya fue aplicado a una factura (útil en informes y cálculos de residual).

        Casos de uso y beneficios:
        - Empresas que usan cuentas segregadas para anticipos (438 / 407) y quieren que los cobros/pagos marcados como anticipos se registren en esas cuentas automáticamente.
        - Aplicación y conciliación automática de anticipos cuando se valida una factura ligada a un pedido con pagos anticipados.
        - Mejor exactitud en el cálculo del saldo de pedido y del residual de la factura teniendo en cuenta anticipos (tanto locales como globales no conciliados).

        Requisitos y compatibilidad:
        - Diseñado para Odoo 15.
        - Dependencias: `account`, `sale_advance_payment`, `purchase_advance_payment`.
        - ADVERTENCIA: Este módulo NO es compatible con el módulo `l10n_es_sale_downpayment_yostesis`. Si un pedido tiene anticipos simples disponibles (advance_payment), el downpayment será bloqueado automáticamente. Elige uno u otro sistema de anticipos para cada pedido, no ambos simultáneamente.

        Configuración recomendada:
        1. En Contabilidad → Configuración → Ajustes, sección "Anticipos", configurar:
           - `Cuenta anticipos clientes (438)`: Cuenta donde se registran los anticipos de clientes.
           - `Cuenta anticipos proveedores (407)`: Cuenta donde se registran los anticipos a proveedores.
           - `Diario de aplicación de anticipos`: Diario donde se crean los asientos de reversión. Si se deja vacío, se usa un diario general por defecto.
        2. (Opcional) Añadir la cuenta `572002000` como cuenta de liquidez preferente para anticipos de venta — se usa como destino cuando es posible, o se recurre al suspense del diario.

        Limitaciones / Consideraciones:
        - El módulo asume que las cuentas 438 (clientes) y 407 (proveedores) están presentes o bien configuradas en la compañía. Si no existen, el comportamiento cae a búsquedas por código y eventualmente a errores de usuario en pantallas (por diseño).
        - El ajuste automático puede cambiar cuentas en asientos de pagos simples; al instalar en producción, probar en entorno de pruebas y revisar los movimientos generados.

        Este módulo centraliza lógicas muy habituales en la contabilidad española sobre anticipos y facilita conciliaciones y cierres de pedidos/facturas.
    """,
    "license": "AGPL-3",
    "author": "Yostesis",
    "website": "Yostesis",
    "category": "Accounting",
    "maintainers": ["Yostesis"],
    "depends": [
        "account",
        "sale_advance_payment",
        "purchase_advance_payment",
        ],
    "data": [
        # "views/res_company_view.xml",
        "views/res_config_settings_views.xml",
        "views/sale_order_view.xml",
        "report/report_invoice_advance_totals.xml",
    ],
    "application": False,
    "installable": True,
}
