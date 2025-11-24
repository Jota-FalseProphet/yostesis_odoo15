#addons-self-made/yostesis/supplier_confirming_yostesis/models/account_move.py
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
                continue

            if any(
                line.account_internal_type == "receivable"
                for line in move.line_ids
            ):
                continue

            company = move.company_id
            suspense_account = getattr(
                company, "account_journal_suspense_account_id", False
            )

            # NUEVO: si el asiento usa la cuenta de anticipos de clientes (438),
            # lo tratamos como anticipo de cliente y NO aplicamos lógica de confirming.
            advance_customer_account = getattr(
                company, "account_advance_customer_id", False
            )
            if advance_customer_account and any(
                line.account_id.id == advance_customer_account.id
                for line in move.line_ids
            ):
                continue

            has_advance_407 = any(
                line.account_id.code
                and line.account_id.code.startswith("407")
                for line in move.line_ids
            )

            if has_advance_407 and suspense_account:
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
                continue

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
