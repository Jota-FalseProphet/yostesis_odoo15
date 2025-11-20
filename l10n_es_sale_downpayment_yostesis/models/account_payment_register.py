# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountPaymentRegister(models.TransientModel):
    _inherit = "account.payment.register"

    # Importante: por defecto False. No lo tomamos del contexto directamente,
    # lo fijamos nosotros en default_get/create para que no "oscile".
    is_advance = fields.Boolean(default=False)

    # ---------------------------
    # Helpers de contexto / 438
    # ---------------------------
    def _moves_from_context(self):
        model = self.env.context.get("active_model")
        ids = self.env.context.get("active_ids") or []
        if not ids and self.env.context.get("active_id"):
            ids = [self.env.context["active_id"]]
        if model == "account.move":
            moves = self.env["account.move"].browse(ids)
        elif model == "account.move.line":
            lines = self.env["account.move.line"].browse(ids)
            moves = lines.mapped("move_id")
        else:
            moves = self.env["account.move"]
        return moves.filtered(lambda m: m.move_type in ("out_invoice", "out_refund"))

    def _acc438(self, company):
        acc = getattr(company, "account_advance_customer_id", False)
        if acc:
            return acc
        return self.env["account.account"].with_company(company).search([
            ("company_id", "=", company.id),
            ("code", "=like", "438%"),
            ("deprecated", "=", False),
        ], limit=1, order="code")

    def _has_advance(self, move):
        # downpayment por SO
        try:
            if hasattr(move, "_is_downpayment_invoice") and move._is_downpayment_invoice():
                return True
        except Exception:
            pass
        # 438 abierta
        acc438 = self._acc438(move.company_id)
        if not acc438:
            return False
        return bool(move.line_ids.filtered(
            lambda l: not l.display_type and l.account_id.id == acc438.id and not l.reconciled
        ))

    def _no_receivable_payable_open(self, move):
        return not bool(move.line_ids.filtered(
            lambda l: not l.display_type
            and l.account_id.internal_type in ("receivable", "payable")
            and not l.reconciled
        ))

    def _pending_from_438(self, move, acc438):
        lines = move.line_ids.filtered(lambda l: not l.display_type and l.account_id.id == acc438.id and not l.reconciled)
        if not lines:
            return 0.0, 0.0, False
        if move.move_type == "out_invoice":
            tgt = lines.filtered(lambda l: l.debit > 0)
        else:
            tgt = lines.filtered(lambda l: l.credit > 0)
        amount_ccy = sum(tgt.mapped("debit")) - sum(tgt.mapped("credit"))
        if not move.currency_id or move.currency_id == move.company_currency_id:
            return amount_ccy, 0.0, False
        amount_cur = sum(tgt.mapped("amount_currency"))
        return amount_ccy, amount_cur, move.currency_id.id

    # ---------------------------
    # Decisión de "modo" estable
    # ---------------------------
    def _decide_is_advance(self, move):
        """Modo anticipo SOLO si: (hay 438 pendiente) y (no hay 430/400 abierta).
        Ignoramos 'is_advance' de contexto para evitar falsos positivos.
        """
        if not move or move.move_type not in ("out_invoice", "out_refund"):
            return False
        if not self._has_advance(move):
            return False
        # Si hay 430 abierta, que vaya por el flujo estándar
        if not self._no_receivable_payable_open(move):
            return False
        return True

    # ---------------------------
    # Overrides defensivos (core) — miro SOLO self.is_advance
    # ---------------------------
    def _get_available_lines(self):
        if any(self.mapped('is_advance')):
            # Evita que el core busque 430/400 (y lance el UserError)
            return self.env['account.move.line']
        return super(AccountPaymentRegister, self)._get_available_lines()

    def _get_batches(self):
        """
        En modo anticipo devolvemos un batch 'dummy' con payment_values completo
        usando los valores del propio wizard, para que los compute() del core
        queden satisfechos.
        """
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        batches = []

        for w in adv:
            mv = w._moves_from_context()
            move = mv[:1] if mv else self.env['account.move']
            company = w.company_id or (move.company_id if move else self.env.company)
            partner = w.partner_id or (move.commercial_partner_id if move else self.env['res.partner'])
            payment_values = {
                'partner_id': partner.id or False,
                'partner_type': w.partner_type or 'customer',
                'payment_type': w.payment_type or 'inbound',
                'currency_id': (w.currency_id and w.currency_id.id) or ((move and move.currency_id.id) or company.currency_id.id),
                'company_id': company.id,
                'journal_id': (w.journal_id and w.journal_id.id) or False,
                'partner_bank_id': (w.partner_bank_id and w.partner_bank_id.id) or (partner and partner.bank_ids[:1].id) or False,
                'communication': w.communication or (move and _("Cobro anticipo %s") % (move.name or move.ref or "")) or "",
                'amount': w.amount or 0.0,
            }
            batches.append({
                'lines': self.env['account.move.line'],  # vacío pero válido
                'payment_values': payment_values,
                'batch_key': (
                    payment_values['company_id'],
                    payment_values['partner_id'] or 0,
                    payment_values['currency_id'],
                    payment_values['journal_id'] or 0,
                    'advance',
                ),
            })

        if std:
            batches += super(AccountPaymentRegister, std)._get_batches()
        return batches

    def _compute_from_lines(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            w.can_edit_wizard = True
        if std:
            super(AccountPaymentRegister, std)._compute_from_lines()

    def _compute_journal_id(self):
        adv = self.filtered(lambda w: w.is_advance and w.journal_id)
        std = self - adv
        if std:
            super(AccountPaymentRegister, std)._compute_journal_id()

    def _compute_can_edit_wizard(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            w.can_edit_wizard = True
        if std:
            super(AccountPaymentRegister, std)._compute_can_edit_wizard()

    def _compute_amount(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        if std:
            super(AccountPaymentRegister, std)._compute_amount()

    def _compute_company_id(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            mv = w._moves_from_context()
            move = mv[:1] if mv else self.env['account.move']
            w.company_id = (move and move.company_id) or self.env.company
        if std:
            super(AccountPaymentRegister, std)._compute_company_id()

    def _compute_source_amount(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            w.source_amount = w.amount or 0.0
        if std:
            super(AccountPaymentRegister, std)._compute_source_amount()

    def _compute_available_partner_bank_ids(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            mv = w._moves_from_context()
            move = mv[:1] if mv else self.env['account.move']
            partner = (move and move.commercial_partner_id) or self.env['res.partner']
            w.available_partner_bank_ids = partner.bank_ids
        if std:
            super(AccountPaymentRegister, std)._compute_available_partner_bank_ids()

    def _compute_partner_bank_id(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            if w.partner_bank_id:
                continue
            mv = w._moves_from_context()
            move = mv[:1] if mv else self.env['account.move']
            partner = (move and move.commercial_partner_id) or self.env['res.partner']
            w.partner_bank_id = partner.bank_ids[:1] if partner else False
        if std:
            super(AccountPaymentRegister, std)._compute_partner_bank_id()

    def _compute_available_payment_method_line_ids(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            j = w.journal_id
            if not j:
                w.available_payment_method_line_ids = self.env['account.payment.method.line']
                continue
            inbound = (w.payment_type or 'inbound') == 'inbound'
            w.available_payment_method_line_ids = (
                j.inbound_payment_method_line_ids if inbound else j.outbound_payment_method_line_ids
            )
        if std:
            super(AccountPaymentRegister, std)._compute_available_payment_method_line_ids()

    def _compute_payment_method_line_id(self):
        adv = self.filtered(lambda w: w.is_advance)
        std = self - adv
        for w in adv:
            if w.payment_method_line_id:
                continue
            j = w.journal_id
            if not j:
                w.payment_method_line_id = False
                continue
            inbound = (w.payment_type or 'inbound') == 'inbound'
            lines = j.inbound_payment_method_line_ids if inbound else j.outbound_payment_method_line_ids
            w.payment_method_line_id = lines[:1] if lines else False
        if std:
            super(AccountPaymentRegister, std)._compute_payment_method_line_id()

    # ---------------------------
    # default_get / create / acción
    # ---------------------------
    @api.model
    def default_get(self, fields_list):
        moves = self._moves_from_context()
        if len(moves) != 1:
            return super().default_get(fields_list)

        move = moves[0]
        # Fijamos el modo UNA VEZ aquí
        is_adv = self._decide_is_advance(move)
        if not is_adv:
            return super().default_get(fields_list)

        company = move.company_id
        acc438 = self._acc438(company)
        amt_ccy, amt_cur, cur_id = self._pending_from_438(move, acc438)

        journal = self.env["account.journal"].with_company(company).search(
            [("company_id", "=", company.id), ("type", "in", ["bank", "cash"])],
            limit=1, order="sequence,id"
        )
        if not journal:
            raise UserError(_("Configura un diario de banco o caja en la compañía."))

        res, setv = {}, (lambda n, v: res.update({n: v}) if n in fields_list else None)
        setv("is_advance", True)
        setv("payment_date", fields.Date.context_today(self))
        setv("partner_id", move.commercial_partner_id.id)
        setv("partner_type", "customer")
        setv("payment_type", "inbound" if move.move_type == "out_invoice" else "outbound")
        setv("journal_id", journal.id)
        setv("company_id", company.id)
        if cur_id:
            setv("currency_id", cur_id)
            setv("amount", amt_cur or 0.0)
        else:
            setv("currency_id", company.currency_id.id)
            setv("amount", amt_ccy or 0.0)
        setv("source_amount", res.get("amount", 0.0))
        setv("communication", _("Cobro anticipo %s") % (move.name or move.ref or ""))
        return res

    @api.model
    def create(self, vals):
        """
        Fijamos is_advance en la creación (si no viene ya en vals) para que
        los compute() siempre miren un flag estable y no haya "primer clic no hace nada".
        """
        if "is_advance" not in vals:
            moves = self._moves_from_context()
            move = moves and moves[:1] or False
            vals = dict(vals)
            vals["is_advance"] = bool(move and self._decide_is_advance(move))
            # En modo anticipo, rellenamos defaults mínimamente por si faltan
            if vals["is_advance"] and move:
                vals.setdefault("company_id", move.company_id.id)
                vals.setdefault("partner_type", "customer")
                vals.setdefault("payment_type", "inbound" if move.move_type == "out_invoice" else "outbound")
        return super().create(vals)

    def action_create_payments(self):
        """
        Si is_advance es False -> flujo estándar de Odoo (super()).
        Si is_advance es True -> asiento manual 438<->banco y conciliación.
        """
        self.ensure_one()

        # ----- Flujo estándar -----
        if not self.is_advance:
            return super().action_create_payments()

        # ----- Flujo manual de anticipo -----
        moves = self._moves_from_context()
        move = moves[:1] if moves else self.env['account.move']

        company = (move and move.company_id) or self.company_id or self.env.company
        partner = (move and move.commercial_partner_id) or self.partner_id

        acc438 = self._acc438(company)
        if not acc438:
            raise UserError(_("Configura una 438 en la compañía."))
        if not acc438.reconcile:
            acc438.write({"reconcile": True})

        journal = self.journal_id
        if not journal or not journal.default_account_id:
            raise UserError(_("El diario debe tener cuenta por defecto."))

        # Importe desde 438 (si hay move) o desde el propio wizard
        if move:
            amt_ccy, amt_cur, cur_id = self._pending_from_438(move, acc438)
        else:
            if self.currency_id and self.currency_id != company.currency_id:
                cur_id = self.currency_id.id
                amt_cur = self.amount
                amt_ccy = self.currency_id._convert(amt_cur, company.currency_id, company, self.payment_date)
            else:
                cur_id, amt_cur, amt_ccy = False, 0.0, self.amount

        # Respeta lo que puso el usuario en el wizard
        if self.amount and self.amount > 0:
            if self.currency_id and self.currency_id != company.currency_id:
                cur_id = self.currency_id.id
                amt_cur = self.amount
                amt_ccy = self.currency_id._convert(amt_cur, company.currency_id, company, self.payment_date)
            else:
                cur_id, amt_cur, amt_ccy = False, 0.0, self.amount

        if not amt_ccy and not amt_cur:
            raise UserError(_("No hay importe pendiente en 438 para esta factura."))

        ref = self.communication or (
            move and _("Cobro anticipo %s") % (move.name or move.ref or "")
        ) or _("Cobro anticipo")

        inbound = True
        if move:
            inbound = move.move_type in ('out_invoice', 'out_receipt')
        elif self.payment_type:
            inbound = (self.payment_type == 'inbound')

        if inbound:
            bank_debit, bank_credit = amt_ccy, 0.0
            adv_debit, adv_credit = 0.0, amt_ccy
            adv_amt_cur = -amt_cur
        else:
            bank_debit, bank_credit = 0.0, amt_ccy
            adv_debit, adv_credit = amt_ccy, 0.0
            adv_amt_cur = amt_cur

        vals = {
            "journal_id": journal.id,
            "date": self.payment_date,
            "ref": ref,
            "line_ids": [
                (0, 0, {
                    "name": ref,
                    "account_id": journal.default_account_id.id,
                    "partner_id": partner.id,
                    "debit": bank_debit,
                    "credit": bank_credit,
                    "currency_id": cur_id,
                    "amount_currency": amt_cur if cur_id else 0.0,
                }),
                (0, 0, {
                    "name": ref,
                    "account_id": acc438.id,
                    "partner_id": partner.id,
                    "debit": adv_debit,
                    "credit": adv_credit,
                    "currency_id": cur_id,
                    "amount_currency": adv_amt_cur if cur_id else 0.0,
                }),
            ],
        }
        # Asegura asiento tipo 'entry' en diario de banco/caja
        vals.update({"move_type": "entry"})
        Move = self.env["account.move"].with_company(company).with_context(
            default_move_type="entry", type="entry", default_type="entry"
        )
        pay_move = Move.create(vals)
        pay_move.action_post()

        # Si veníamos de una factura concreta, conciliamos 438
        if move:
            inv_438_open = move.line_ids.filtered(lambda l: not l.display_type and l.account_id.id == acc438.id and not l.reconciled)
            pay_438_open = pay_move.line_ids.filtered(lambda l: not l.display_type and l.account_id.id == acc438.id and not l.reconciled)
            if inv_438_open and pay_438_open:
                (inv_438_open + pay_438_open).reconcile()

        return {"type": "ir.actions.act_window_close"}
