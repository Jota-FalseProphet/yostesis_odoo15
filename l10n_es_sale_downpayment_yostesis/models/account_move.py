# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_acc438(self, company):
        acc = getattr(company, "account_advance_customer_id", False)
        if not acc:
            acc = self.env["account.account"].with_company(company).search([
                ("company_id", "=", company.id),
                ("code", "=like", "438%"),
                ("deprecated", "=", False),
            ], limit=1, order="code")
        return acc

    def _is_downpayment_invoice(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            return False
        inv_lines = self.invoice_line_ids.filtered(lambda l: not l.display_type)
        if not inv_lines:
            return False
        if any(inv_lines.mapped("sale_line_ids.is_downpayment")):
            return all(any(sl.is_downpayment for sl in l.sale_line_ids) for l in inv_lines)
        def _is_dp(l):
            n = (l.name or "").lower()
            pn = (l.product_id.name or "").lower()
            return ("anticipo" in n or "down payment" in n or "anticipo" in pn or ("down" in pn and "payment" in pn))
        return all(_is_dp(l) for l in inv_lines)

    @api.model
    def create(self, vals_list):
        moves = super().create(vals_list)
        for move in moves.filtered(lambda m: m.state == "draft" and m.move_type in ("out_invoice", "out_refund") and m._is_downpayment_invoice()):
            move.with_context(check_move_validity=False)._recompute_payment_terms_lines()
        return moves

    def _advance_438_apply_if_needed(self):
        dp = self.filtered(lambda m: m._is_downpayment_invoice())
        others = (self - dp)
        res = None
        if others:
            try:
                res = super(AccountMove, others)._advance_438_apply_if_needed()
            except AttributeError:
                res = None
        return res

    def _recompute_payment_terms_lines(self):
        res = super()._recompute_payment_terms_lines()
        for move in self:
            if move.move_type not in ("out_invoice", "out_refund"):
                continue
            if not move._is_downpayment_invoice():
                continue

            company = move.company_id
            acc438 = getattr(company, "account_advance_customer_id", False) or self.env["account.account"].with_company(company).search([
                ("company_id", "=", company.id),
                ("code", "=like", "438%"),
                ("deprecated", "=", False),
            ], limit=1, order="code")
            if not acc438:
                continue
            if not acc438.reconcile:
                acc438.write({"reconcile": True})

            recv_lines = move.line_ids.filtered(
                lambda l: not l.display_type and l.account_id.internal_type == "receivable"
            )
            if not recv_lines:
                continue

            recv_account = recv_lines[0].account_id

            old_438 = move.line_ids.filtered(
                lambda l: not l.display_type and l.account_id.id == acc438.id and l.exclude_from_invoice_tab
            )

            other = move.line_ids.filtered(
                lambda l: not l.display_type
                and l.id not in recv_lines.ids
                and l.id not in old_438.ids
            )

            balance_sum = sum(other.mapped("balance"))
            amount_ccy = -balance_sum
            amount_cur = 0.0
            if move.currency_id and move.currency_id != move.company_currency_id:
                amount_cur = -sum(other.mapped("amount_currency"))

            cmds = []
            cmds += [(2, l.id, False) for l in old_438]
            cmds += [(2, l.id, False) for l in recv_lines]

            if amount_ccy or amount_cur:
                vals = {
                    "move_id": move.id,
                    "name": _("Saldo anticipo"),
                    "partner_id": move.commercial_partner_id.id,
                    "account_id": recv_account.id,  # 430 del partner
                    "debit": amount_ccy if amount_ccy > 0 else 0.0,
                    "credit": -amount_ccy if amount_ccy < 0 else 0.0,
                    "exclude_from_invoice_tab": True,
                }
                if move.currency_id and move.currency_id != move.company_currency_id:
                    vals.update({
                        "currency_id": move.currency_id.id,
                        "amount_currency": amount_cur,
                    })
                cmds.append((0, 0, vals))

            if cmds:
                move.with_context(check_move_validity=False).write({"line_ids": cmds})

        return res


    def _dp_438_open_lines(self):
        self.ensure_one()
        acc438 = self._get_acc438(self.company_id)
        if not acc438:
            return self.env["account.move.line"]
        return self.line_ids.filtered(lambda l: not l.display_type and l.account_id.id == acc438.id and not l.reconciled and (l.debit > 0 or l.credit > 0))




    # def _compute_payment_state(self):
    #     super()._compute_payment_state()
    #     for move in self:
    #         if move.move_type in ("out_invoice", "out_refund") and move._is_downpayment_invoice():
    #             lines = move._dp_438_debit_lines()
    #             if not lines:
    #                 continue
    #             if all(l.reconciled for l in lines):
    #                 move.payment_state = "paid"
    #             elif any(l.matched_credit_ids or l.matched_debit_ids for l in lines):
    #                 move.payment_state = "in_payment"
    #             else:
    #                 move.payment_state = "not_paid"

    # def _compute_invoice_payment_state(self):
    #     super()._compute_invoice_payment_state()
    #     for move in self:
    #         if move.move_type in ("out_invoice", "out_refund") and move._is_downpayment_invoice():
    #             lines = move._dp_438_debit_lines()
    #             if not lines:
    #                 continue
    #             if all(l.reconciled for l in lines):
    #                 move.invoice_payment_state = "paid"
    #             elif any(l.matched_credit_ids or l.matched_debit_ids for l in lines):
    #                 move.invoice_payment_state = "in_payment"
    #             else:
    #                 move.invoice_payment_state = "not_paid"
    def _compute_payment_state(self):
        try:
            super(AccountMove, self)._compute_payment_state()
        except AttributeError:
            pass
        for move in self:
            if move.move_type in ("out_invoice", "out_refund"):
                lines = move._dp_438_open_lines()
                if lines:
                    if any(l.matched_credit_ids or l.matched_debit_ids for l in lines):
                        val = "in_payment" if "payment_state" in self._fields and any(k == "in_payment" for k, _ in self._fields["payment_state"].selection or []) else "not_paid"
                        move.payment_state = val
                    else:
                        move.payment_state = "not_paid"


    def _compute_invoice_payment_state(self):
        if "invoice_payment_state" not in self._fields:
            return
        try:
            super(AccountMove, self)._compute_invoice_payment_state()
        except AttributeError:
            pass
        for move in self:
            if move.move_type in ("out_invoice", "out_refund"):
                lines = move._dp_438_open_lines()
                if lines:
                    if any(l.matched_credit_ids or l.matched_debit_ids for l in lines):
                        move.invoice_payment_state = "in_payment" if any(k == "in_payment" for k,_ in self._fields["invoice_payment_state"].selection or []) else "not_paid"
                    else:
                        move.invoice_payment_state = "not_paid"


    def action_post(self):
        res = super().action_post()
        try:
            self._compute_payment_state()
        except Exception:
            pass
        return res

    def action_register_payment(self):
        self.ensure_one()
        if self.move_type not in ("out_invoice", "out_refund"):
            return super().action_register_payment()
        is_adv = False
        try:
            is_adv = self._is_downpayment_invoice()
        except Exception:
            is_adv = False
        if not is_adv and hasattr(self, "_dp_438_open_lines"):
            try:
                is_adv = bool(self._dp_438_open_lines())
            except Exception:
                is_adv = False
        if not is_adv:
            return super().action_register_payment()
        ctx = dict(self.env.context, active_model="account.move", active_ids=[self.id], is_advance=True)
        return {
            "type": "ir.actions.act_window",
            "res_model": "account.payment.register",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }
