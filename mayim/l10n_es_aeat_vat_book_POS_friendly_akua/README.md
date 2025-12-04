# l10n_es_aeat_vat_book_POS_friendly_akua

Pequeño módulo para Odoo 15 que hace compatible el módulo `l10n_es_aeat_vat_book` con tickets generados desde POS cuando esos tickets son anónimos (sin partner ni NIF).

## Qué hace

- Añade el campo `vat_book_pos_anonymous` en `account.journal` para marcar diarios de POS cuyo historial de tickets debe tratarse como anónimo.
- En `pos.config`, al crear o actualizar la configuración, marca automáticamente `journal_id.vat_book_pos_anonymous = True` si se asigna un diario.
- Ajusta `l10n.es.vat.book._check_exceptions` para ignorar líneas procedentes de diarios POS marcados como anónimos: evita que se generen excepciones tipo "Without Partner" o "Without VAT" para tickets POS anónimos.

## Instalar y configurar

1. Coloca el módulo en tu carpeta de addons y actualiza la lista de módulos.
2. Instálalo desde el panel de Aplicaciones.
3. Ve a la configuración del Punto de Venta (POS) y asigna el `journal` que uses para tickets.
   - Al crear/editar el `pos.config` el diario será marcado con `VAT Book POS` anónimo automáticamente.

## Ejemplo de uso

- Un ticket POS anónimo (sin partner) generado con un diario marcado como `vat_book_pos_anonymous` ya no generará excepciones en el Libro de IVA AEAT.

## Notas

- No añade vistas nuevas ni datos adicionales; es una mejora del comportamiento que depende de:
  - `l10n_es_aeat_vat_book`
  - `akua_pos` (o cualquier configuración POS que use `pos.config` y `journal_id`).

## Compatibilidad

- Odoo 15

## Licencia

- LGPL-3
