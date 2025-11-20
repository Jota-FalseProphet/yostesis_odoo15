# Punt_staging3/puntmobles/account_advance_yostesis/models/account_move.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        res = super().action_post()
        self._advance_438_apply_if_needed()     
        self._advance_407_apply_if_needed()
        return res

    def _advance_438_apply_if_needed(self):
        invoices = self.filtered(
            lambda m: m.move_type == "out_invoice" and m.state == "posted"
        )
        if not invoices:
            return

        AccountMove = self.env["account.move"]
        Journal = self.env["account.journal"]

        for inv in invoices:
            company   = inv.company_id
            acc_adv   = company.account_advance_customer_id
            if not acc_adv:
                continue

            sale_orders = inv.mapped("line_ids.sale_line_ids.order_id")
            if not sale_orders:
                continue

            payments = sale_orders.mapped("account_payment_ids").filtered(
                lambda p: p.state == "posted"
            )
            if not payments:
                continue

            partner   = inv.commercial_partner_id
            adv_lines = payments.mapped("move_id.line_ids").filtered(
                lambda l: l.account_id == acc_adv
                and l.partner_id == partner
                and not l.reconciled
                and l.company_id == company
            )
            if not adv_lines:
                continue

            credit_available = -sum(adv_lines.mapped("balance"))
            if credit_available <= 0:
                continue

            invoice_residual = inv.amount_residual
            if invoice_residual <= 0:
                continue

            apply_amt = min(credit_available, invoice_residual)
            if not apply_amt:
                continue

            journal = payments[0].journal_id
            if journal.type not in ("general", "bank", "cash"):
                journal = Journal.search(
                    [("type", "=", "general"), ("company_id", "=", company.id)],
                    limit=1,
                )
            if not journal:
                raise UserError(
                    _(
                        "No hay diario disponible para registrar el traspaso de anticipos (438→430) en la compañía %s."
                    )
                    % company.display_name
                )

            recv_line = inv.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )[:1]
            if not recv_line:
                continue

            bridge_move = AccountMove.create(
                {
                    "ref": _("Aplicación anticipo %s")
                    % (inv.name or inv.ref or inv.id),
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": inv.invoice_date
                    or fields.Date.context_today(self),
                    "line_ids": [
                        (
                            0,
                            0,
                            {
                                "name": _("Aplicación anticipo a %s")
                                % (inv.name or inv.ref or inv.id),
                                "account_id": acc_adv.id,
                                "debit": apply_amt,
                                "partner_id": partner.id,
                            },
                        ),
                        (
                            0,
                            0,
                            {
                                "name": _("Aplicación anticipo a %s")
                                % (inv.name or inv.ref or inv.id),
                                "account_id": recv_line.account_id.id,
                                "credit": apply_amt,
                                "partner_id": partner.id,
                            },
                        ),
                    ],
                }
            )
            bridge_move.action_post()

            bridge_recv_line = bridge_move.line_ids.filtered(
                lambda l: l.account_id == recv_line.account_id and not l.reconciled
            )
            (recv_line | bridge_recv_line).reconcile()

            bridge_adv_line = bridge_move.line_ids.filtered(
                lambda l: l.account_id == acc_adv and not l.reconciled
            )
            (adv_lines | bridge_adv_line).reconcile()

            if apply_amt and inv.state == "posted":
                note_text = _(
                    "Anticipos aplicados en esta factura: %s"
                ) % (inv.currency_id.symbol + " %.2f" % apply_amt)

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
                    ("code", "=like", "4383%"),
                    ("company_id", "=", company.id),
                    ("deprecated", "=", False),
                ],
                limit=1,
            ) or self.env["account.account"].search(
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
            applied_company = sum(lines.mapped("debit"))
            if not applied_company:
                return 0.0

            return comp_curr._convert(applied_company, inv_curr, company, conv_date)

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

