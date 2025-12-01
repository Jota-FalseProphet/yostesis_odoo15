# Automated Confirming Yostesis

Módulo para Odoo 15 que automatiza la cancelación y conciliación final del confirming (factoring).

## Resumen

Este módulo busca en las órdenes de cobro los efectos descontados/confirming que han vencido, crea automáticamente asientos de cancelación que reclasifican la deuda de riesgo a deuda real y realiza las conciliaciones necesarias entre las líneas involucradas.

Es ideal para empresas que utilizan confirming/factoring y quieren automatizar la generación de asientos de cancelación y conciliación con el banco.

## Funcionalidades principales

- Añade campos y funcionalidad en contabilidad:
  - `account.move`: `confirming_cancel_move_id` (método compute) y `is_confirming_cancel_move` (flag en asientos generados por cancelling).
  - `account.move.line`: `yostesis_confirming_cancel_move_id` (Many2one hacia el asiento de cancelación generado).

- Cron programado que ejecuta `_cron_confirming_auto_conciliation` sobre `account.payment.order` para:
  - Identificar líneas reconciliadas que pertenezcan a cuentas de riesgo (ej. 4311) con vencimientos en el rango configurado.
  - Crear un asiento de tipo `entry` que cancela la deuda y reclasifica el riesgo (usa la cuenta deuda configurada y la cuenta riesgo configurada).
  - Postear (opcional) el asiento de cancelación y conciliarlo con la línea de riesgo original.

- Panel de configuración (`Settings`) para habilitar el cron y configurar las cuentas y el diario.

- Extensiones visuales:
  - Modifica el widget de pagos en la vista de factura para mostrar "Pagado al Vencimiento" para líneas de confirming.
  - Ajusta la plantilla del informe de factura para mostrar la etiqueta adecuada cuando una línea de confirming se haya procesado.

## Parámetros de configuración (res.config.settings)

Los valores se almacenan en `ir.config_parameter` con el prefijo `yostesis_confirming`:

- `yostesis_confirming.confirming_payment_mode_id` — (Many2one) Payment Mode que identifica órdenes de confirming.
- `yostesis_confirming.confirming_from_date` — (Date) Fecha mínima para que el cron procese vencimientos.
- `yostesis_confirming.confirming_risk_account_id` — (Many2one) Cuenta de riesgo (p. ej. 4311) que representa deuda factoring.
- `yostesis_confirming.confirming_debt_account_id` — (Many2one) Cuenta donde se registrará la deuda real (p. ej. 5208).
- `yostesis_confirming.confirming_journal_id` — (Many2one) Diario para generar los asientos de cancelación.
- `yostesis_confirming.confirming_enable_cron` — (Boolean) Flag para activar o desactivar el cron.

## Dependencias

- `account`
- `account_payment_mode`
- `account_payment_order`
- `l10n_es_payment_order_confirming_aef` (localización / módulos que generan las órdenes de cobro con property 'Confirming')

## Instalación

1. Colocar el módulo en la ruta de addons.
2. Actualizar la lista de aplicaciones en Odoo.
3. Instalar el módulo.

## Configuración rápida

1. Ir a Ajustes → Contabilidad → Confirming (sección añadida por el módulo).
2. Establecer:
   - Modo de cobro para identificar órdenes de confirming.
   - Cuenta riesgo (p. ej. 4311)
   - Cuenta deuda (p. ej. 5208)
   - Diario donde se crearán asientos de cancelación
3. Activar el cron si se desea procesamiento automático diario (o dejar desactivado y ejecutar manualmente).

## Cómo funciona el cron (comportamiento)

- El cron (registro en `data/confirming_cron.xml`) invoca `account.payment.order`._cron_confirming_auto_conciliation().
- El método filtra órdenes (no en borrador) y, si se configuran `payment_mode_id`, aplica la selección por modo de cobro.
- Para cada payment_line con una fecha de vencimiento válida y conciliada, si existe una línea asociada en la cuenta de riesgo, crea un movimiento contable de tipo `entry` que:
  - Debita la cuenta deuda (p.ej. 5208)
  - Acredita la cuenta riesgo (p.ej. 4311)
  - Marca el nuevo `account.move` como `is_confirming_cancel_move = True` y vincula las líneas originales con `yostesis_confirming_cancel_move_id`.
- Posteriormente (si no está en modo de prueba) postea el movimiento y realiza la conciliación entre la línea de riesgo original y la línea creada en el asiento cancelatorio.

## Pruebas / modos de desarrollo

- Para evitar postear los asientos durante pruebas automáticas, llamar al método con el contexto `confirming_test_only=True` (el código evita `action_post()` cuando este flag está presente).

## Reportes y interfaz

- `reports/report_invoice_confirming.xml`: modifica plantilla del informe de factura para mostrar la etiqueta "Pagado al Vencimiento" (o traducción) en líneas de confirming.
- `static/src/xml/account_confirming_payment.xml`: extensión QWeb para el widget de pagos de facturas.

## Notas y consideraciones

- Asegúrate de que las cuentas y el diario estén configuradas y pertenezcan a la compañía correcta antes de activar el cron en producción.
- Prueba la funcionalidad en un entorno de testing con algunos casos reales para verificar conciliaciones.

## Licencia

AGPL-3
