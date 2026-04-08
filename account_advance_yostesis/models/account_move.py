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

            recv_line = inv.line_ids.filtered(
                lambda l: l.account_id.internal_type == "receivable"
            )[:1]
            if not recv_line:
                continue

            inv_curr = inv.currency_id
            comp_curr = company.currency_id

            # Usar el diario configurado para aplicación de anticipos, o buscar uno general
            journal = company.advance_transfer_journal_id
            if not journal:
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

            pay_moves = payments.mapped("move_id").sorted("date")

            for pay_move in pay_moves:
                adv_lines = pay_move.line_ids.filtered(
                    lambda l: l.account_id == acc_adv
                    and l.partner_id == partner
                    and not l.reconciled
                    and l.company_id == company
                )
                if not adv_lines:
                    continue

                if inv_curr == comp_curr:
                    credit_available_ccy = -sum(adv_lines.mapped("balance"))
                    if credit_available_ccy <= 0:
                        continue

                    invoice_residual_ccy = inv.amount_residual
                    if invoice_residual_ccy <= 0:
                        break

                    apply_amt_ccy = min(credit_available_ccy, invoice_residual_ccy)
                    if not apply_amt_ccy:
                        continue

                    apply_amt_cur = apply_amt_ccy

                else:
                    # Moneda extranjera: usar los valores ORIGINALES del anticipo
                    # sin reconvertir, para mantener el tipo de cambio del día del pago.

                    # Disponible en moneda extranjera (ej: CAD)
                    residuals_cur = adv_lines.mapped("amount_residual_currency")
                    if not any(residuals_cur):
                        residuals_cur = adv_lines.mapped("amount_currency")
                    credit_available_cur = -sum(residuals_cur)
                    if credit_available_cur <= 0:
                        continue

                    # Disponible en moneda de compañía (EUR) - valor ORIGINAL del anticipo
                    credit_available_ccy = -sum(adv_lines.mapped("balance"))
                    if credit_available_ccy <= 0:
                        continue

                    invoice_residual_cur = recv_line.amount_residual_currency
                    if invoice_residual_cur <= 0:
                        break

                    # Calcular cuánto aplicar en moneda extranjera
                    apply_amt_cur = min(credit_available_cur, invoice_residual_cur)
                    if not apply_amt_cur:
                        continue

                    # Calcular el EUR proporcional usando el tipo de cambio ORIGINAL del anticipo
                    # en lugar de reconvertir con el tipo de cambio de la factura.
                    if credit_available_cur:
                        ratio = apply_amt_cur / credit_available_cur
                    else:
                        ratio = 1.0
                    apply_amt_ccy = credit_available_ccy * ratio

                # Usar la fecha de la factura como fecha contable del asiento de reversión
                advance_date = inv.invoice_date or inv.date or fields.Date.context_today(self)

                bridge_vals = {
                    "ref": _("Aplicación anticipo %s")
                    % (inv.name or inv.ref or inv.id),
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": advance_date,
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

            # note_amount = inv._get_advance_applied_amount()
            # if note_amount and inv.state == "posted":
            #     note_text = _(
            #         "Anticipos aplicados en esta factura: %s"
            #     ) % (inv.currency_id.symbol + " %.2f" % note_amount)

            #     already = inv.invoice_line_ids.filtered(
            #         lambda l: l.display_type == "line_note"
            #         and "Anticipos aplicados" in (l.name or "")
            #     )
            #     if not already:
            #         try:
            #             inv.write(
            #                 {
            #                     "invoice_line_ids": [
            #                         (
            #                             0,
            #                             0,
            #                             {
            #                                 "name": note_text,
            #                                 "display_type": "line_note",
            #                                 "sequence": 9999,
            #                             },
            #                         )
            #                     ]
            #                 }
            #             )
            #         except Exception:
            #             inv.message_post(body=note_text, subtype_xmlid="mail.mt_note")

            note_amount = inv._get_advance_applied_amount()
            if note_amount and inv.state == "posted":
                note_text = _(
                    "Anticipos aplicados en esta factura: %s"
                ) % (inv.currency_id.symbol + " %.2f" % note_amount)

                # Para evitar que se reescriban comisionistas al tocar invoice_line_ids,
                # dejamos este dato solo en el chatter.
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

            inv_curr = inv.currency_id
            comp_curr = company.currency_id

            # Disponible en EUR (balance original del anticipo)
            credit_available_ccy = sum(adv_lines.mapped("balance"))
            if credit_available_ccy <= 0:
                continue

            pay_line = inv.line_ids.filtered(lambda l: l.account_id.internal_type == "payable")[:1]
            if not pay_line:
                continue

            # Usar el diario configurado para aplicación de anticipos, o el del pago, o buscar uno general
            journal = company.advance_transfer_journal_id
            if not journal:
                journal = pays[0].journal_id
                if journal.type not in ("general", "bank", "cash"):
                    journal = self.env["account.journal"].search([("type","=","general"),("company_id","=",company.id)], limit=1)
            if not journal:
                continue

            # Usar la fecha de la factura como fecha contable del asiento de reversión
            advance_date = inv.invoice_date or inv.date or fields.Date.context_today(self)

            if inv_curr == comp_curr:
                # Factura en EUR: usar valores directamente
                invoice_residual_ccy = inv.amount_residual
                apply_amt_ccy = min(credit_available_ccy, invoice_residual_ccy)
                if not apply_amt_ccy:
                    continue

                bridge = self.env["account.move"].create({
                    "ref": _("Aplicación anticipo proveedor %s") % (inv.name or inv.ref or inv.id),
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": advance_date,
                    "line_ids": [
                        (0, 0, {
                            "name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                            "account_id": pay_line.account_id.id,
                            "debit": apply_amt_ccy,
                            "partner_id": partner.id,
                        }),
                        (0, 0, {
                            "name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                            "account_id": acc_407.id,
                            "credit": apply_amt_ccy,
                            "partner_id": partner.id,
                        }),
                    ],
                })
            else:
                # Factura en moneda extranjera: usar valores ORIGINALES del anticipo
                # sin reconvertir, para mantener el tipo de cambio del día del pago.

                # Disponible en moneda extranjera
                residuals_cur = adv_lines.mapped("amount_residual_currency")
                if not any(residuals_cur):
                    residuals_cur = adv_lines.mapped("amount_currency")
                credit_available_cur = sum(residuals_cur)  # Para proveedores es positivo (débito)
                if credit_available_cur <= 0:
                    continue

                invoice_residual_cur = pay_line.amount_residual_currency
                if invoice_residual_cur >= 0:  # Para proveedores el residual es negativo
                    continue

                # Calcular cuánto aplicar en moneda extranjera
                apply_amt_cur = min(credit_available_cur, -invoice_residual_cur)
                if not apply_amt_cur:
                    continue

                # Calcular el EUR proporcional usando el tipo de cambio ORIGINAL del anticipo
                if credit_available_cur:
                    ratio = apply_amt_cur / credit_available_cur
                else:
                    ratio = 1.0
                apply_amt_ccy = credit_available_ccy * ratio

                bridge = self.env["account.move"].create({
                    "ref": _("Aplicación anticipo proveedor %s") % (inv.name or inv.ref or inv.id),
                    "move_type": "entry",
                    "journal_id": journal.id,
                    "date": advance_date,
                    "currency_id": inv_curr.id,
                    "line_ids": [
                        (0, 0, {
                            "name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                            "account_id": pay_line.account_id.id,
                            "debit": apply_amt_ccy,
                            "amount_currency": apply_amt_cur,
                            "currency_id": inv_curr.id,
                            "partner_id": partner.id,
                        }),
                        (0, 0, {
                            "name": _("Aplicación anticipo a %s") % (inv.name or inv.ref or inv.id),
                            "account_id": acc_407.id,
                            "credit": apply_amt_ccy,
                            "amount_currency": -apply_amt_cur,
                            "currency_id": inv_curr.id,
                            "partner_id": partner.id,
                        }),
                    ],
                })

            bridge.action_post()

            bridge_pay = bridge.line_ids.filtered(lambda l: l.account_id == pay_line.account_id and not l.reconciled)
            (pay_line | bridge_pay).reconcile()
            bridge_adv = bridge.line_ids.filtered(lambda l: l.account_id == acc_407 and not l.reconciled)
            (adv_lines | bridge_adv).reconcile()

            # Crear líneas de nota separadas por cada anticipo/pago con su fecha
            lines_to_add = []
            for adv_line in adv_lines:
                pay_move = adv_line.move_id
                # Convertir a la moneda de la factura
                if inv.currency_id == company.currency_id:
                    amt_display = adv_line.balance
                else:
                    amt_display = inv.currency_id._convert(
                        adv_line.balance, inv.currency_id, company, pay_move.date or fields.Date.today()
                    )
                
                note_text = _(
                    "Anticipo pagado el %s: %s"
                ) % (
                    fields.Date.to_string(pay_move.date),
                    inv.currency_id.symbol + " %.2f" % abs(amt_display)
                )
                lines_to_add.append({
                    "name": note_text,
                    "display_type": "line_note",
                    "sequence": 9999 + len(lines_to_add),
                })

            if lines_to_add:
                try:
                    inv.write({
                        "invoice_line_ids": [
                            (0, 0, line_data) for line_data in lines_to_add
                        ]
                    })
                except Exception:
                    for line_data in lines_to_add:
                        inv.message_post(body=line_data['name'], subtype_xmlid="mail.mt_note")
                
    
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



    def _get_reconciled_info_JSON_values(self):
        """
        Override para mostrar los pagos originales del pedido en lugar de los asientos de reversión.
        Cuando hay anticipos aplicados (asientos bridge 438→430 o 407→400), busca y devuelve
        los pagos originales del pedido en lugar de los bridges.
        """
        # Llamar al método original
        reconciled_vals = super()._get_reconciled_info_JSON_values()

        # Solo procesar facturas de cliente y proveedor
        if self.move_type not in ('out_invoice', 'in_invoice'):
            return reconciled_vals

        company = self.company_id
        partner = self.commercial_partner_id

        # Obtener cuentas de anticipo configuradas
        if self.move_type == 'out_invoice':
            acc_advance = company.account_advance_customer_id
            sale_orders = self.mapped("line_ids.sale_line_ids.order_id")
            if not sale_orders and self.invoice_origin:
                sale_orders = self.env['sale.order'].search([('name', '=', self.invoice_origin)], limit=1)
            source_orders = sale_orders
        else:  # in_invoice
            acc_advance = company.account_advance_supplier_id
            source_orders = self.mapped("line_ids.purchase_line_id.order_id")

        if not acc_advance or not source_orders:
            return reconciled_vals

        # Buscar asientos de reversión (bridges) en los reconciled_vals
        bridge_move_ids = []
        for val in reconciled_vals:
            if val.get('ref') and 'Aplicación anticipo' in val.get('ref', ''):
                # Este es probablemente un asiento de reversión
                move_id = val.get('move_id')
                if move_id:
                    bridge_move_ids.append(move_id)

        if not bridge_move_ids:
            return reconciled_vals

        # Buscar los pagos originales del pedido
        original_payments = source_orders.mapped('account_payment_ids').filtered(
            lambda p: p.state == 'posted'
        )

        if not original_payments:
            return reconciled_vals

        # Construir el mapeo de bridges → pagos originales
        bridge_to_payment = {}
        for bridge_id in bridge_move_ids:
            bridge_move = self.env['account.move'].browse(bridge_id)

            # Buscar líneas del bridge en cuenta de anticipo que estén reconciliadas
            bridge_adv_lines = bridge_move.line_ids.filtered(
                lambda l: l.account_id == acc_advance and l.reconciled
            )

            # Buscar qué pago original está reconciliado con este bridge
            for adv_line in bridge_adv_lines:
                for part_rec in adv_line.matched_debit_ids | adv_line.matched_credit_ids:
                    # Obtener la línea contraria (del pago original)
                    counterpart_line = part_rec.debit_move_id if part_rec.credit_move_id == adv_line else part_rec.credit_move_id

                    # Verificar si esta línea pertenece a un pago original
                    if counterpart_line.move_id in original_payments.mapped('move_id'):
                        bridge_to_payment[bridge_id] = counterpart_line.move_id
                        break
                if bridge_id in bridge_to_payment:
                    break

        # Reemplazar los valores de los bridges con los de los pagos originales
        new_reconciled_vals = []
        for val in reconciled_vals:
            move_id = val.get('move_id')
            if move_id in bridge_to_payment:
                # Reemplazar con el pago original
                original_move = bridge_to_payment[move_id]
                original_payment = original_payments.filtered(lambda p: p.move_id == original_move)

                if original_payment:
                    # Crear el diccionario con los datos del pago original
                    new_val = {
                        'name': original_payment.name,
                        'move_id': original_move.id,
                        'amount': val['amount'],  # Mantener el monto aplicado
                        'date': original_move.date,
                        'ref': original_move.ref or original_payment.name,
                        'account_payment_id': original_payment.id,
                    }
                    new_reconciled_vals.append(new_val)
                else:
                    new_reconciled_vals.append(val)
            else:
                new_reconciled_vals.append(val)

        return new_reconciled_vals

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

