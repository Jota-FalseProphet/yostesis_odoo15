# Punt_staging3/puntmobles/account_advance_yostesis/models/account_move.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        self._advance_438_apply_if_needed()     
        self._advance_407_apply_if_needed()
        self._fix_confirming_payment_mode_from_sale()
        return res
    
    # def _post(self, soft=True):
    #     moves = super()._post(soft=soft)
    #     moves._simple_customer_payment_apply_if_needed()
    #     moves._simple_supplier_payment_apply_if_needed()
    #     return moves

    def _advance_438_apply_if_needed(self):
        invoices = self.filtered(
            lambda m: m.move_type == "out_invoice" and m.state == "posted"
        )
        if not invoices:
            return

        AccountMove = self.env["account.move"]
        Journal = self.env["account.journal"]
        SaleOrder = self.env["sale.order"]

        for inv in invoices:
            company = inv.company_id
            acc_adv = company.account_advance_customer_id
            if not acc_adv:
                continue

            partner = inv.commercial_partner_id
            if not partner:
                continue

            sale_orders = inv.mapped("line_ids.sale_line_ids.order_id")
            if not sale_orders and inv.invoice_origin:
                sale_orders = SaleOrder.search(
                    [("name", "=", inv.invoice_origin)], limit=1
                )
            if not sale_orders:
                continue

            payments = sale_orders.mapped("account_payment_ids").filtered(
                lambda p: p.state == "posted"
            )
            if not payments:
                continue

            adv_lines = payments.mapped("move_id.line_ids").filtered(
                lambda l: l.account_id == acc_adv
                and l.partner_id == partner
                and not l.reconciled
                and l.company_id == company
            )
            if not adv_lines:
                continue

            recv_line = inv.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )[:1]
            if not recv_line:
                continue

            inv_curr = inv.currency_id
            comp_curr = company.currency_id

            if inv_curr == comp_curr:
                credit_available_ccy = -sum(adv_lines.mapped("balance"))
                if credit_available_ccy <= 0:
                    continue

                invoice_residual_ccy = inv.amount_residual
                if invoice_residual_ccy <= 0:
                    continue

                apply_amt_ccy = min(credit_available_ccy, invoice_residual_ccy)
                if not apply_amt_ccy:
                    continue

                apply_amt_cur = apply_amt_ccy

            else:
                residuals_cur = adv_lines.mapped("amount_residual_currency")
                if not residuals_cur:
                    residuals_cur = adv_lines.mapped("amount_currency")
                credit_available_cur = -sum(residuals_cur)
                if credit_available_cur <= 0:
                    continue

                invoice_residual_cur = recv_line.amount_residual_currency
                if invoice_residual_cur <= 0:
                    continue

                apply_amt_cur = min(credit_available_cur, invoice_residual_cur)
                if not apply_amt_cur:
                    continue

                conv_date = inv.invoice_date or inv.date or fields.Date.context_today(self)
                apply_amt_ccy = inv_curr._convert(
                    apply_amt_cur, comp_curr, company, conv_date
                )

            journal = Journal.search(
                [("type", "=", "general"), ("company_id", "=", company.id)],
                limit=1,
            )
            if not journal:
                raise UserError(
                    _(
                        "No hay diario general disponible para registrar el traspaso de anticipos (438→430) en la compañía %s."
                    )
                    % company.display_name
                )

            bridge_vals = {
                "ref": _("Aplicación anticipo %s")
                % (inv.name or inv.ref or inv.id),
                "move_type": "entry",
                "journal_id": journal.id,
                "date": inv.invoice_date
                or fields.Date.context_today(self),
            }

            if inv_curr == comp_curr:
                line_adv = {
                    "name": _("Aplicación anticipo a %s")
                    % (inv.name or inv.ref or inv.id),
                    "account_id": acc_adv.id,
                    "debit": apply_amt_ccy,
                    "partner_id": partner.id,
                }
                line_recv = {
                    "name": _("Aplicación anticipo a %s")
                    % (inv.name or inv.ref or inv.id),
                    "account_id": recv_line.account_id.id,
                    "credit": apply_amt_ccy,
                    "partner_id": partner.id,
                }
            else:
                line_adv = {
                    "name": _("Aplicación anticipo a %s")
                    % (inv.name or inv.ref or inv.id),
                    "account_id": acc_adv.id,
                    "debit": apply_amt_ccy,
                    "amount_currency": apply_amt_cur,
                    "currency_id": inv_curr.id,
                    "partner_id": partner.id,
                }
                line_recv = {
                    "name": _("Aplicación anticipo a %s")
                    % (inv.name or inv.ref or inv.id),
                    "account_id": recv_line.account_id.id,
                    "credit": apply_amt_ccy,
                    "amount_currency": -apply_amt_cur,
                    "currency_id": inv_curr.id,
                    "partner_id": partner.id,
                }
                bridge_vals["currency_id"] = inv_curr.id

            bridge_vals["line_ids"] = [
                (0, 0, line_adv),
                (0, 0, line_recv),
            ]

            bridge_move = AccountMove.create(bridge_vals)
            bridge_move.action_post()

            bridge_recv_line = bridge_move.line_ids.filtered(
                lambda l: l.account_id == recv_line.account_id and not l.reconciled
            )
            (recv_line | bridge_recv_line).reconcile()

            bridge_adv_line = bridge_move.line_ids.filtered(
                lambda l: l.account_id == acc_adv and not l.reconciled
            )
            (adv_lines | bridge_adv_line).reconcile()

            # Nota en divisa de la factura
            note_amount = apply_amt_ccy if inv_curr == comp_curr else apply_amt_cur

            if note_amount and inv.state == "posted":
                note_text = _(
                    "Anticipos aplicados en esta factura: %s"
                ) % (inv.currency_id.symbol + " %.2f" % note_amount)

                already = inv.invoice_line_ids.filtered(
                    lambda l: l.display_type == "line_note"
                    and "Anticipos aplicados" in (l.name or "")
                )
                if already:
                    continue

                try:
                    inv.write(
                        {
                            "invoice_line_ids": [
                                (
                                    0,
                                    0,
                                    {
                                        "name": note_text,
                                        "display_type": "line_note",
                                        "sequence": 9999,
                                    },
                                )
                            ]
                        }
                    )
                except Exception:
                    inv.message_post(body=note_text, subtype_xmlid="mail.mt_note")



    def _advance_407_apply_if_needed(self):
        invoices = self.filtered(lambda m: m.move_type == "in_invoice" and m.state == "posted")
        if not invoices:
            return
        for inv in invoices:
            company = inv.company_id
            acc_407 = company.account_advance_supplier_id
            if not acc_407:
                continue

            purchases = inv.mapped("line_ids.purchase_line_id.order_id")
            if not purchases:
                continue

            pays = purchases.mapped("account_payment_ids").filtered(lambda p: p.state == "posted")
            if not pays:
                continue

            partner = inv.commercial_partner_id
            adv_lines = pays.mapped("move_id.line_ids").filtered(
                lambda l: l.account_id == acc_407 and l.partner_id == partner and not l.reconciled and l.company_id == company
            )
            if not adv_lines:
                continue

            credit_available = sum(adv_lines.mapped("balance")) 
            if credit_available <= 0:
                continue

            inv_ccy = company.currency_id
            if inv.currency_id == inv_ccy:
                residual_company = inv.amount_residual
            else:
                residual_company = inv.currency_id._convert(
                    inv.amount_residual, inv_ccy, company, inv.invoice_date or fields.Date.context_today(self)
                )
            apply_amt = min(credit_available, residual_company)
            if not apply_amt:
                continue

            pay_line = inv.line_ids.filtered(lambda l: l.account_id.internal_type == "payable")[:1]
            if not pay_line:
                continue

            journal = pays[0].journal_id
            if journal.type not in ("general", "bank", "cash"):
                journal = self.env["account.journal"].search([("type","=","general"),("company_id","=",company.id)], limit=1)
            if not journal:
                continue

            bridge = self.env["account.move"].create({
                "ref": _("Aplicación anticipo proveedor %s") % (inv.name or inv.ref or inv.id),
                "move_type": "entry",
                "journal_id": journal.id,
                "date": inv.invoice_date or fields.Date.context_today(self),
                "line_ids": [
                    (0,0,{"name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                        "account_id": pay_line.account_id.id, "debit": apply_amt, "partner_id": partner.id}),
                    (0,0,{"name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                        "account_id": acc_407.id, "credit": apply_amt, "partner_id": partner.id}),
                ],
            })
            bridge.action_post()

            bridge_pay = bridge.line_ids.filtered(lambda l: l.account_id == pay_line.account_id and not l.reconciled)
            (pay_line | bridge_pay).reconcile()
            bridge_adv = bridge.line_ids.filtered(lambda l: l.account_id == acc_407 and not l.reconciled)
            (adv_lines | bridge_adv).reconcile()

            note = _("Anticipos de proveedor aplicados en esta factura: %s") % (
                inv.currency_id.symbol + " " + inv.currency_id.round(
                    inv.company_currency_id._convert(apply_amt, inv.currency_id, company, inv.date or fields.Date.today())
                ).__format__("f")
            )
            try:
                inv.write({"invoice_line_ids":[(0,0,{"name": note, "display_type":"line_note", "sequence": 9999})]})
            except Exception:
                inv.message_post(body=note, subtype_xmlid="mail.mt_note")
                
    
    def _simple_customer_payment_apply_if_needed(self):
        Pay = self.env["account.payment"]
        Account = self.env["account.account"]

        for move in self:
            pay = Pay.search([("move_id", "=", move.id)], limit=1)
            if not pay:
                continue
            if pay.partner_type != "customer":
                continue
            if pay.payment_type != "inbound":
                continue
            if pay.is_advance:
                continue
            if move.payment_order_id:
                continue

            acc_4312 = Account.search(
                [
                    ("code", "like", "4312%"),
                    ("company_id", "=", move.company_id.id),
                ],
                limit=1,
            )
            if not acc_4312:
                continue

            line_4311 = move.line_ids.filtered(
                lambda l: l.account_id.code
                and l.account_id.code.startswith("4311")
            )[:1]
            if not line_4311:
                continue

            recv_lines = move.line_ids.filtered(
                lambda l: l.account_internal_type == "receivable"
            )
            if not recv_lines:
                continue

            line_4311.with_context(
                skip_account_move_synchronization=True
            ).write({"account_id": acc_4312.id})
            
    def _simple_supplier_payment_apply_if_needed(self):
        Pay = self.env["account.payment"]
        Account = self.env["account.account"]

        for move in self:
            if move.journal_id.type not in ("bank", "cash"):
                continue

            pay = Pay.search([("move_id", "=", move.id)], limit=1)
            if not pay:
                continue
            if pay.partner_type != "supplier":
                continue
            if pay.payment_type != "outbound":
                continue
            if pay.is_advance:
                continue
            if move.payment_order_id:
                continue

            acc_411 = Account.search(
                [
                    ("code", "like", "411%"),
                    ("company_id", "=", move.company_id.id),
                ],
                limit=1,
            )
            if not acc_411:
                continue

            line_5205 = move.line_ids.filtered(
                lambda l: l.account_id.code
                and l.account_id.code.startswith("5205")
            )[:1]
            if not line_5205:
                continue

            payable_lines = move.line_ids.filtered(
                lambda l: l.account_internal_type == "payable"
            )
            if len(payable_lines) != 1:
                continue
            if not payable_lines[0].account_id.code or not payable_lines[
                0
            ].account_id.code.startswith("400"):
                continue

            line_5205.with_context(
                skip_account_move_synchronization=True
            ).write({"account_id": acc_411.id})

    
    def _fix_confirming_payment_mode_from_sale(self):
        """
        Si la factura proviene de un pedido cuya forma de pago es el modo
        de Factoring configurado, se fuerza ese mismo modo en la factura
        incluso después de validar, para que el cron de factoring la detecte.

        Evita que account_payment_partner (u otros módulos) machaquen
        el payment_mode_id con el modo por defecto del cliente.
        """
        icp = self.env["ir.config_parameter"].sudo()
        payment_mode_param = icp.get_param(
            "yostesis_confirming.confirming_payment_mode_id"
        )
        confirming_mode = (
            self.env["account.payment.mode"].browse(int(payment_mode_param))
            if payment_mode_param
            else False
        )
        if not confirming_mode:
            return

        SaleOrder = self.env["sale.order"]

        for move in self.filtered(
            lambda m: m.move_type in ("out_invoice", "out_refund")
        ):
            # localizar pedido origen
            sale = SaleOrder.search([("name", "=", move.invoice_origin)], limit=1)
            if not sale:
                sale = move.line_ids.sale_line_ids.order_id[:1]
            if not sale:
                continue

            # sólo tocamos si el pedido usa el modo de FACTORING
            if sale.payment_mode_id.id != confirming_mode.id:
                continue

            # si la factura no tiene ese mismo modo, lo forzamos
            if move.payment_mode_id.id != confirming_mode.id:
                move.with_context(tracking_disable=True).write(
                    {"payment_mode_id": confirming_mode.id}
                )



    def _get_advance_applied_amount(self):
        self.ensure_one()
        company = self.company_id
        partner = self.commercial_partner_id
        conv_date = self.invoice_date or self.date or fields.Date.context_today(self)
        comp_curr = company.currency_id
        inv_curr = self.currency_id

        def _search_bridges():
            return self.env["account.move"].search(
                [
                    ("ref", "ilike", self.name or self.ref or ""),
                    ("state", "=", "posted"),
                    ("company_id", "=", company.id),
                    # ("move_type", "=", "entry"),  # si quieres limitar a asientos generales
                ]
            )

        if self.move_type == "out_invoice":
            acc_438 = company.account_advance_customer_id or self.env["account.account"].search(
                [
                    ("code", "=like", "438%"),
                    ("company_id", "=", company.id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )
            if not acc_438:
                return 0.0

            bridges = _search_bridges()
            if not bridges:
                return 0.0

            lines = bridges.mapped("line_ids").filtered(
                lambda l: l.account_id == acc_438 and l.partner_id == partner
            )
            if not lines:
                return 0.0

            if inv_curr == comp_curr:
                applied_company = sum(lines.mapped("debit"))
                if not applied_company:
                    return 0.0
                return applied_company

            applied_foreign = -sum(lines.mapped("amount_currency"))
            if not applied_foreign:
                return 0.0

            return applied_foreign


        if self.move_type == "in_invoice":
            acc_407 = company.account_advance_supplier_id or self.env["account.account"].search(
                [
                    ("code", "=like", "407%"),
                    ("company_id", "=", company.id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )
            if not acc_407:
                return 0.0

            bridges = _search_bridges()
            if not bridges:
                return 0.0

            lines = bridges.mapped("line_ids").filtered(
                lambda l: l.account_id == acc_407 and l.partner_id == partner
            )
            applied_company = sum(lines.mapped("credit"))
            if not applied_company:
                return 0.0

            return comp_curr._convert(applied_company, inv_curr, company, conv_date)

        return 0.0

