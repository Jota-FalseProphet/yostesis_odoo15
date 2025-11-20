from odoo import models


class AccountMove(models.Model):
    _inherit = "account.move"

    def _post_confirming_adjustment(self):
        """
        Ajuste posterior al post de los apuntes de diarios de Confirming Proveedores.

        - Solo actúa sobre asientos SIN cuentas 'receivable' (es decir, NO toca
          operaciones de confirming de clientes, que llevan 430).

        - Si el diario tiene 'confirming_payment_account_id' (p.ej. 5208...) y el
          asiento NO es un anticipo (no hay 407*), se reasignan las líneas "other"
          a esa cuenta.

        - Si el asiento incluye 407* (anticipo a proveedores) y la compañía tiene
          'account_journal_suspense_account_id' (p.ej. 572001000), la línea de
          liquidez se pasa a esa cuenta de suspense usando el contexto
          'skip_account_move_synchronization' para no romper el payment.
        """
        for move in self:
            journal = move.journal_id
            confirming_account = getattr(
                journal, "confirming_payment_account_id", False
            )
            if not confirming_account:
                # Diario sin cuenta de confirming -> no hacemos nada
                continue

            # IMPORTANTE: si el asiento tiene cuentas 'receivable' (430, etc.),
            # lo consideramos flujo de CLIENTES y NO lo tocamos. Eso lo gestiona
            # el módulo automated_confirming_yostesis.
            if any(
                line.account_internal_type == "receivable"
                for line in move.line_ids
            ):
                continue

            company = move.company_id
            suspense_account = getattr(
                company, "account_journal_suspense_account_id", False
            )

            # ¿Este asiento tiene una 407*? => anticipo de proveedor
            has_advance_407 = any(
                line.account_id.code
                and line.account_id.code.startswith("407")
                for line in move.line_ids
            )

            if has_advance_407 and suspense_account:
                # CASO ANTICIPO DE COMPRA:
                # Forzamos que la "línea de liquidez" (no 407, no receivable/payable)
                # vaya a la cuenta de suspense global.
                liquidity_lines = move.line_ids.filtered(
                    lambda l: (
                        l.account_internal_type not in ("receivable", "payable")
                        and not (
                            l.account_id.code
                            and l.account_id.code.startswith("407")
                        )
                    )
                )
                if liquidity_lines:
                    liquidity_lines.with_context(
                        skip_account_move_synchronization=True
                    ).write({"account_id": suspense_account.id})
                # No aplicamos la lógica normal de confirming en este caso
                continue

            # COMPORTAMIENTO NORMAL DE CONFIRMING PROVEEDORES (NO ANTICIPOS):
            other_lines = move.line_ids.filtered(
                lambda l: l.account_internal_type not in ("receivable", "payable")
            )
            if other_lines:
                other_lines.with_context(
                    skip_account_move_synchronization=True
                ).write({"account_id": confirming_account.id})

    def _post(self, soft=True):
        moves = super()._post(soft=soft)
        moves._post_confirming_adjustment()
        return moves
