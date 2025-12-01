# account_advance_yostesis

Módulo para Odoo 15 que mejora la gestión de anticipos (clientes y proveedores) asignando cuentas específicas (438 y 407) y automatizando aplicación y conciliación de anticipos con facturas.

## Resumen

Este módulo centraliza varias mejoras contables relacionadas con anticipos:

- Registra cobros de cliente marcados como anticipos en la cuenta 438 (si está configurada) y evita tocar la 430 salvo que sea necesario como sustitución controlada.
- Registra pagos a proveedor marcados como anticipos en la cuenta 407 (si está configurada).
- Ajusta asientos simples de pagos anticipados para que la otra parte vaya a la cuenta de liquidez preferente (572002000) o al suspense configurado.
- Automatiza la aplicación de anticipos (creación de asientos puente) cuando se valida una factura asociada a un pedido con anticipos, y realiza la conciliación apropiada.
- Mejora los cálculos del saldo residual de pedidos (sale.order / purchase.order) teniendo en cuenta anticipos aplicados y globales no conciliados.

### Campos y cálculos en Sale Order

- `advance_amount_paid_order`: total de anticipos ligados directamente al pedido (convertido a la moneda del pedido si aplica).
- `advance_amount_paid_applied`: importe de anticipos ya aplicados en facturas publicadas (movimientos puente 438→430).
- `advance_amount_paid_available`: diferencia entre `advance_amount_paid_order` y `advance_amount_paid_applied` (anticipos aún disponibles).
- `commercial_balance_after_advances`: saldo comercial del pedido (importe total − anticipos aplicados/ligados).
- `advance_amount_partner_global`: total de anticipos globales no conciliados del cliente (cuentas 438 a nivel partner).

### Wizards y fixes

- `sale_advance_close_fix.make_advance_payment`: asegura que la respuesta del wizard no incluya `context`/`params` extra que provoquen warnings en controladores web.
- `account.voucher.wizard` y `account.voucher.wizard.purchase`: cuando crean pagos de anticipo preparan `is_advance = True` y seleccionan la cuenta destino apropiada (438 para ventas, 407 para compras).

### Comportamiento en account.payment

- Campos y flags:
  - `is_advance` — marca interna indicando que el pago es un anticipo.
- Comportamiento:
  - Forzar la cuenta contrapartida hacia la cuenta de anticipos configurada (438/407) según tipo de pago y relación con purchase/sale.
  - Para anticipos de venta intenta usar `572002000` como cuenta de liquidez; si no existe, cae al suspense configurado en la compañía o journal.

### Aplicación automática de anticipos en account.move

- Al postear facturas (`out_invoice`/`in_invoice`) el módulo busca anticipos relacionados a pedidos/ordenes de compra y, si hay saldo disponible, crea movimientos puente que aplican la parte de anticipo al recibo/pago de la factura. Posteriormente, concilia las líneas correspondientes.
- Métodos clave: `_advance_438_apply_if_needed`, `_advance_407_apply_if_needed`, `_get_advance_applied_amount`.

## Características clave

- Campos en la compañía (`res.company`):
  - `account_advance_customer_id` — cuenta de anticipos de clientes (438)
  - `account_advance_supplier_id` — cuenta de anticipos a proveedores (407)
  - `advance_transfer_journal_id` — diario por defecto para asientos puente 438→430 / 407→400 cuando se aplican anticipos

- Comportamiento extendido de `account.payment`:
  - Marca pagos como `is_advance` cuando vienen de asistentes de pago de anticipos.
  - Ajusta las cuentas de contrapartida y liquidez para anticipos (uso preferente de 572002000 o suspense configurable).

- Aplicación automática de anticipos (al postear facturas):
  - Para facturas de cliente (`out_invoice`): busca anticipos hechos en pedidos vinculados, crea un asiento puente (438→430) y concilia líneas.
  - Para facturas de proveedor (`in_invoice`): busca anticipos en compras vinculadas, crea un asiento puente (407→400) y concilia líneas.

## Requisitos

- Odoo 15
- Dependencias de módulo: `account`, `sale_advance_payment`, `purchase_advance_payment`

## Instalación

1. Colocar el módulo dentro de la carpeta `addons` (o en tus rutas de addons).
2. Actualizar lista de aplicaciones en Odoo y **actualizar/reiniciar** el servidor si procede.
3. Instalar el módulo desde el panel de apps.

## Configuración recomendada

1. Ir a Ajustes → Compañía → Configurar la compañía.
2. Rellenar *Cuenta de anticipos de clientes (438)* y *Cuenta de anticipos a proveedores (407)* con cuentas válidas y conciliables si procede.
3. (Opcional) Configurar *Diario para traspasos de anticipos* si quieres fijar un diario específico para los asientos puente.
4. (Opcional) Asegurarse de que existe la cuenta `572002000` si quieres que se use como cuenta preferente de liquidez para anticipos de venta.

## Uso / Flujo típico

1. Registrar un pago de anticipo desde el asistente de cobro (o desde `account.payment` y marcar `is_advance`). El asiento usará la cuenta 438 y la 572002000 o el suspense configurado.
2. Crear/validar la factura asociada al pedido. Al publicar la factura, el módulo intentará aplicar los anticipos del pedido creando un asiento puente y conciliando las líneas correspondientes.
3. En compras, el proceso es análogo pero usando 407 para anticipos.

## Notas y consideraciones

- El módulo hace cambios automáticos en asientos y conciliaciones: probar en un entorno de testing antes de activar en producción.
- Si la cuenta 438 o 407 no está presente, el módulo intenta buscar cuentas por código (por ejemplo 4383% o 438% para ventas), y para proveedores 407%.

## Mantenedores / Autor

Desarrollado por Yostesis.

## Licencia

AGPL-3
