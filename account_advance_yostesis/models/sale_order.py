# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_round, float_compare


class SaleOrder(models.Model):
    _inherit = "sale.order"

    # ------------------------------------------------------------------
    # CAMPOS
    # ------------------------------------------------------------------
    advance_amount_paid_order = fields.Monetary(
        string="Anticipos del pedido",
        compute="_compute_advance_amounts",
        currency_field="currency_id",
        store=False,
    )
    advance_amount_paid_applied = fields.Monetary(
        string="Anticipos aplicados en facturas",
        compute="_compute_advance_amounts",
        currency_field="currency_id",
        store=False,
    )
    advance_amount_paid_available = fields.Monetary(
        string="Anticipos disponibles",
        compute="_compute_advance_amounts",
        currency_field="currency_id",
        store=False,
    )
    commercial_balance_after_advances = fields.Monetary(
        string="Saldo comercial (total − anticipos)",
        compute="_compute_advance_amounts",
        currency_field="currency_id",
        store=False,
    )
    advance_amount_partner_global = fields.Monetary(
        string="Anticipos globales del cliente",
        compute="_compute_advance_amounts",
        currency_field="currency_id",
        store=False,
    )

    # ------------------------------------------------------------------
    # CÁLCULO DE IMPORTES DE ANTICIPOS
    # ------------------------------------------------------------------
    @api.depends(
        "order_line.price_total",
        "currency_id",
        "company_id",
        "account_payment_ids",
        "account_payment_ids.move_id.state",
        "account_payment_ids.amount",
        "account_payment_ids.currency_id",
        "account_payment_ids.move_id.line_ids.account_id",
        "account_payment_ids.move_id.line_ids.balance",
        "invoice_ids.state",
        "invoice_ids.move_type",
        "invoice_ids.amount_residual",
    )
    def _compute_advance_amounts(self):
        AccountMoveLine = self.env["account.move.line"]
        company_438_map = {}

        for order in self:
            company = order.company_id
            if company.id not in company_438_map:
                acc = company.account_advance_customer_id or self.env["account.account"].search(
                    [
                        ("code", "=like", "438%"),
                        ("company_id", "=", company.id),
                        ("deprecated", "=", False),
                    ],
                    limit=1,
                )
                company_438_map[company.id] = acc
            acc_438 = company_438_map[company.id]

            currency = order.currency_id or company.currency_id
            rounding = currency.rounding
            paid_order = applied = available = partner_global = 0.0

            if acc_438:
                # 1) ANTICIPOS LIGADOS AL PEDIDO ---------------------------------
                payments = order.account_payment_ids.filtered(
                    lambda p: p.move_id.state == "posted"
                )
                if "is_advance" in self.env["account.payment"]._fields:
                    payments = payments.filtered("is_advance")

                if payments:
                    adv_lines = payments.mapped("move_id.line_ids").filtered(
                        lambda l: l.account_id == acc_438 and l.company_id == company
                    )
                    for l in adv_lines:
                        amt = company.currency_id._convert(
                            -l.balance, currency, company, l.date or fields.Date.today()
                        )
                        paid_order += amt

                    # 2) ANTICIPOS YA APLICADOS EN FACTURAS ----------------------
                    invoices = order.invoice_ids.filtered(
                        lambda m: m.state == "posted" and m.move_type == "out_invoice"
                    )
                    for inv in invoices:
                        recv_lines = inv.line_ids.filtered(
                            lambda l: l.account_id.internal_type == "receivable"
                        )
                        for rl in recv_lines:
                            # contrapartidas conciliadas (430-crédito del puente)
                            c_moves = (
                                rl.matched_debit_ids.debit_move_id
                                + rl.matched_credit_ids.credit_move_id
                            ).mapped("move_id")
                            for mv in c_moves:
                                bridge_438 = mv.line_ids.filtered(
                                    lambda l: l.account_id == acc_438 and l.debit
                                )
                                for l in bridge_438:
                                    amt = company.currency_id._convert(
                                        l.debit, currency, company, l.date or fields.Date.today()
                                    )
                                    applied += amt

                    available = max(paid_order - applied, 0.0)

                # 3) SALDO GLOBAL 438 NO CONCILIADO ------------------------------
                if order.partner_id:
                    partner = order.partner_id.commercial_partner_id
                    global_lines = AccountMoveLine.search(
                        [
                            ("account_id", "=", acc_438.id),
                            ("partner_id", "=", partner.id),
                            ("company_id", "=", company.id),
                            ("reconciled", "=", False),
                        ]
                    )
                    if global_lines:
                        amt_company = -sum(global_lines.mapped("balance"))
                        partner_global = company.currency_id._convert(
                            amt_company, currency, company, fields.Date.today()
                        )

            commercial_balance = order.amount_total - paid_order

            order.advance_amount_paid_order = float_round(paid_order, precision_rounding=rounding)
            order.advance_amount_paid_applied = float_round(applied, precision_rounding=rounding)
            order.advance_amount_paid_available = float_round(available, precision_rounding=rounding)
            order.commercial_balance_after_advances = float_round(
                commercial_balance, precision_rounding=rounding
            )
            order.advance_amount_partner_global = float_round(
                partner_global, precision_rounding=rounding
            )

    # ------------------------------------------------------------------
    # ESTADO DE PAGO / amount_residual
    # ------------------------------------------------------------------
    @api.depends(
        "currency_id",
        "company_id",
        "amount_total",
        "account_payment_ids",
        "account_payment_ids.move_id.state",
        "account_payment_ids.amount",
        "invoice_ids.amount_residual",
        "invoice_ids.amount_total",
        "invoice_ids.currency_id",
    )
    def _compute_advance_payment(self):
        self._compute_advance_amounts()

        for order in self:
            currency = order.currency_id or order.company_id.currency_id
            rounding = currency.rounding

            paid_order = order.advance_amount_paid_order or 0.0
            applied = order.advance_amount_paid_applied or 0.0

            # Pagos registrados directamente en facturas
            invoice_paid = 0.0
            for inv in order.invoice_ids:
                inv_curr = getattr(inv, "company_currency_id", order.company_id.currency_id)
                paid_signed = inv.amount_total_signed - inv.amount_residual_signed
                invoice_paid += (
                    inv_curr._convert(
                        paid_signed, currency, order.company_id, inv.invoice_date or fields.Date.today()
                    )
                    if inv_curr != currency
                    else paid_signed
                )

            # total – anticipos – pagos_factura + anticipos_aplicados
            amount_residual = order.amount_total - paid_order - invoice_paid + applied

            payment_state = (
                "not_paid"
                if currency.is_zero(paid_order) and currency.is_zero(invoice_paid)
                else ("paid" if float_compare(amount_residual, 0.0, precision_rounding=rounding) <= 0 else "partial")
            )

            order.payment_line_ids = False
            order.advance_payment_status = payment_state
            order.amount_residual = float_round(amount_residual, precision_rounding=rounding)
