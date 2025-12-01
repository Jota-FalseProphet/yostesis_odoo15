# addons-self-made/yostesis/supplier_confirming_yostesis/models/account_move.py
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

        - Si el asiento viene de un extracto bancario (tiene statement_line_id) y
          ha quedado con la cuenta de confirming en ambas líneas, se corrige para
          que una línea sea el banco (default_account_id) y la otra la cuenta de
          confirming.
        """
        for move in self:
            journal = move.journal_id
            confirming_account = getattr(
                journal, "confirming_payment_account_id", False
            )
            if not confirming_account:
                continue

            # No tocamos operaciones con cuentas a cobrar (confirming clientes)
            if any(
                line.account_internal_type == "receivable"
                for line in move.line_ids
            ):
                continue

            company = move.company_id
            suspense_account = getattr(
                company, "account_journal_suspense_account_id", False
            )

            # Si el asiento usa la cuenta de anticipos de clientes (438),
            # lo tratamos como anticipo de cliente y NO aplicamos lógica
            # de confirming de proveedores.
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

            # --- NUEVO: casos que vienen de extractos bancarios ---
            # Aquí es donde se rompían los asientos 572 -> 5205 en ambas líneas.
            if any(move.line_ids.mapped("statement_line_id")):
                move._post_confirming_adjustment_bank_statement(
                    confirming_account
                )
                # No seguimos con el resto de lógica para este asiento
                continue

            # Anticipos proveedor (407) con cuenta de suspense configurada
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

            # Resto de asientos de confirming proveedores:
            # reasignamos líneas "other" a la cuenta de confirming.
            other_lines = move.line_ids.filtered(
                lambda l: l.account_internal_type not in ("receivable", "payable")
            )
            if other_lines:
                other_lines.with_context(
                    skip_account_move_synchronization=True
                ).write({"account_id": confirming_account.id})

    def _post_confirming_adjustment_bank_statement(self, confirming_account):
        """
        Corrección específica para asientos de extracto bancario que han quedado
        con la cuenta de confirming en las dos líneas (p.ej. 5205 / 5205).

        Objetivo: dejar el asiento como:
          - Banco (default_account_id del diario) en la línea que representa el
            movimiento de banco.
          - Confirming (confirming_account) en la otra línea.

        Se apoya en el signo de amount del extracto:
          - amount < 0  -> salida de dinero -> banco al HABER.
          - amount > 0  -> entrada de dinero -> banco al DEBE.
        """
        for move in self:
            # Solo nos preocupamos de las líneas que no son a cobrar / a pagar.
            lines = move.line_ids.filtered(
                lambda l: l.account_internal_type not in ("receivable", "payable")
            )

            # Caso típico de extracto: exactamente dos líneas (banco vs contrapartida)
            if len(lines) != 2:
                continue

            # Las dos líneas tienen que estar actualmente en la misma cuenta
            # (la de confirming) para que tenga sentido corregir.
            if len(lines.mapped("account_id")) != 1:
                continue
            if lines[0].account_id.id != confirming_account.id:
                continue

            debit_line = lines.filtered(lambda l: l.debit > 0)
            credit_line = lines.filtered(lambda l: l.credit > 0)
            if not debit_line or not credit_line:
                continue

            bank_account = move.journal_id.default_account_id
            if not bank_account:
                continue

            # Tomamos la línea de extracto para ver el signo del importe
            st_line = (lines.mapped("statement_line_id") or [False])[0]
            amount = getattr(st_line, "amount", 0.0)

            # amount < 0: dinero que sale del banco -> banco al HABER (crédito)
            # amount > 0: dinero que entra al banco -> banco al DEBE
            if amount > 0:
                bank_target_line = debit_line
            elif amount < 0:
                bank_target_line = credit_line
            else:
                # En caso raro de amount = 0, asumimos comportamiento "salida"
                bank_target_line = credit_line

            bank_target_line.with_context(
                skip_account_move_synchronization=True
            ).write({"account_id": bank_account.id})

    def _post(self, soft=True):
        moves = super()._post(soft=soft)

        # Ajuste de confirming proveedores (incluye ahora la corrección
        # específica para extractos bancarios).
        moves._post_confirming_adjustment()

        # Mantengo exactamente tu lógica: si existen estos métodos (definidos
        # en account_advance_yostesis), se llaman desde aquí también.
        if hasattr(moves, "_simple_customer_payment_apply_if_needed"):
            moves._simple_customer_payment_apply_if_needed()

        if hasattr(moves, "_simple_supplier_payment_apply_if_needed"):
            moves._simple_supplier_payment_apply_if_needed()

        return moves
