from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ChangeSaleCustomerWizard(models.TransientModel):
    _name = "change.sale.customer.wizard"
    _description = "Cambiar cliente en pedido confirmado (solo partner_id)"

    sale_id = fields.Many2one(
        "sale.order",
        string="Pedido",
        required=True,
        default=lambda self: self.env.context.get("active_id"),
    )

    new_partner_id = fields.Many2one(
        "res.partner",
        string="Nuevo cliente",
        required=True,
        domain=[("parent_id", "=", False)]
    )

    update_open_pickings = fields.Boolean(
        string="Actualizar partner en albaranes abiertos",
        default=False,
        help="Si se marca, actualiza partner_id en los albaranes no hechos/cancelados."
    )
    update_proc_group = fields.Boolean(
        string="Actualizar partner en el Procurement Group",
        default=False,
        help=(
            "Actualiza el partner del grupo de aprovisionamiento. Recomendado si también cambias la "
            "dirección de entrega o esperas nuevas entregas/backorders. Si no cambias la entrega, "
            "podrías mezclar cliente nuevo con dirección antigua en futuros documentos."
        ),
    )
    update_followers = fields.Boolean(
        string="Actualizar seguidores (chatter)",
        default=False,
        help="Quita al cliente anterior y añade al nuevo como seguidores del pedido."
    )

    update_addresses = fields.Boolean(
        string="Cambiar dirección de Entrega y Facturación", default=False,
        help="Toma las direcciones por defecto del nuevo cliente.")

    recompute_taxes = fields.Boolean(
        string="Recalcular posición fiscal e impuestos", default=True,
        help="Vuelve a calcular la Posición Fiscal del pedido y los impuestos de las líneas.")

    use_partner_pricelist = fields.Boolean(
        string="Usar tarifa del nuevo cliente", default=False,
        help="Antes de recalcular precios, cambia la tarifa del pedido por la del nuevo cliente.")

    recompute_prices = fields.Boolean(
        string="Recalcular precios y descuentos desde la tarifa", default=False,
        help="Recalcula precios y descuentos de todas las líneas con la tarifa del pedido.")

    apply_billing_defaults = fields.Boolean(
        string="Tomar condiciones de pago del nuevo cliente", default=True
    )

    force_breakdown_discount = fields.Boolean(
        string="Forzar % de descuento en líneas", default=True
    )

    note_reason = fields.Char(string="Motivo del cambio")

    ui_addresses_taxes = fields.Boolean(string="Direcciones, fiscalidad y logística", default=False)
    ui_tariff_prices = fields.Boolean(string="Tarifa y precios", default=False)

    @api.onchange('ui_addresses_taxes')
    def _onchange_ui_addresses_taxes(self):
        for w in self:
            flag = w.ui_addresses_taxes
            w.update_addresses = flag
            w.recompute_taxes = flag
            w.apply_billing_defaults = flag
            w.update_open_pickings = flag
            w.update_proc_group = flag

    @api.onchange('ui_tariff_prices')
    def _onchange_ui_tariff_prices(self):
        for w in self:
            flag = w.ui_tariff_prices
            w.use_partner_pricelist = flag
            w.recompute_prices = flag
            w.force_breakdown_discount = flag

    def _payment_has_unreconciled_receivable(self, payment):
        move = payment.move_id
        if not move:
            return False
        receivable_lines = move.line_ids.filtered(lambda l: l.account_id.user_type_id.type == 'receivable')
        return any(not l.reconciled for l in receivable_lines)

    def _posted_payments_linked_to_sale(self, sale):
        Payment = self.env['account.payment']
        if 'sale_id' in Payment._fields:
            return Payment.search([
                ('sale_id', '=', sale.id),
                ('state', '=', 'posted'),
                ('company_id', '=', sale.company_id.id),
            ])
        return Payment.browse()

    def _get_account_advance_customer(self, company):
        Account = self.env['account.account']
        acc_438 = False
        if 'account_advance_customer_id' in self.env['res.company']._fields:
            acc_438 = company.account_advance_customer_id
        if not acc_438:
            acc_438 = Account.search([
                ('code', '=like', '438%'),
                ('company_id', '=', company.id),
                ('deprecated', '=', False),
            ], limit=1)
        return acc_438

    def _posted_advance_payments_by_438_and_ref(self, sale):
        AML = self.env['account.move.line'].with_context(prefetch_fields=False)
        acc_438 = self._get_account_advance_customer(sale.company_id)
        if not acc_438:
            return self.env['account.payment'].browse(), AML.browse()
        domain_eq = [
            ('account_id', '=', acc_438.id),
            ('company_id', '=', sale.company_id.id),
            ('partner_id', '=', sale.partner_id.commercial_partner_id.id),
            ('move_id.state', '=', 'posted'),
            ('move_id.ref', '=', sale.name),
        ]
        cnt = AML.search_count(domain_eq)
        if not cnt:
            return self.env['account.payment'].browse(), AML.browse()
        aml = AML.search(domain_eq, limit=50)
        payments = aml.mapped('move_id.payment_id').filtered(lambda p: p and p.state == 'posted')
        return payments, aml

    def _check_no_advance_payments(self, sale):
        Payment = self.env['account.payment']
        payments_posted = self._posted_payments_linked_to_sale(sale)
        if 'is_advance' in Payment._fields and payments_posted:
            adv_by_flag = payments_posted.filtered(lambda p: p.is_advance)
            if adv_by_flag:
                names = ", ".join(filter(None, adv_by_flag.mapped('name'))) or _("%d pago(s)") % len(adv_by_flag)
                raise UserError(_("No es posible cambiar el cliente porque existen pagos de anticipo vinculados a este pedido.\nPagos afectados: %s\n\nAnule o reasigne esos anticipos antes de cambiar el cliente.") % names)
        unreconciled = payments_posted.filtered(self._payment_has_unreconciled_receivable)
        if unreconciled:
            names = ", ".join(filter(None, unreconciled.mapped('name'))) or _("%d pago(s)") % len(unreconciled)
            raise UserError(_("No es posible cambiar el cliente porque existen pagos posteados vinculados al pedido con saldo pendiente en cuenta por cobrar.\nPagos afectados: %s\n\nConcílielos/reasígnelos antes de cambiar el cliente.") % names)
        adv_by_438_payments, aml = self._posted_advance_payments_by_438_and_ref(sale)
        if adv_by_438_payments:
            names = ", ".join(filter(None, adv_by_438_payments.mapped('name'))) or _("%d pago(s)") % len(adv_by_438_payments)
            raise UserError(_("No es posible cambiar el cliente porque se detectaron pagos de anticipo (438) relacionados con este pedido por la referencia.\nPagos afectados: %s\n\nAnule o reasigne esos anticipos antes de cambiar el cliente.") % names)
        moves_without_payment = aml.mapped('move_id').filtered(lambda m: not m.payment_id)
        if moves_without_payment:
            labels = [m.name or m.ref or str(m.id) for m in moves_without_payment]
            refs = ", ".join(labels) or _("%d asiento(s)") % len(moves_without_payment)
            raise UserError(_("No es posible cambiar el cliente porque se detectaron asientos POSTED en la 438 relacionados con este pedido (por la referencia), sin pago asociado.\nAsientos: %s") % refs)

    def _check_no_accounting_done(self, sale):
        invoices = sale.invoice_ids.filtered(lambda m: m.move_type in ("out_invoice", "out_refund"))
        posted = invoices.filtered(lambda m: m.state == "posted")
        paid = invoices.filtered(lambda m: m.payment_state in ("in_payment", "paid"))
        if posted or paid:
            raise UserError(_("No es posible cambiar el cliente porque existen facturas posteadas o con pagos asociadas a este pedido.\n- Facturas posteadas: %s\n- Facturas con pago: %s") % (", ".join(posted.mapped("name")) or "-", ", ".join(paid.mapped("name")) or "-"))

    def _update_followers(self, sale, old_partner, new_partner):
        Followers = self.env["mail.followers"]
        old = old_partner.commercial_partner_id
        new = new_partner.commercial_partner_id
        Followers.search([("res_model", "=", "sale.order"), ("res_id", "=", sale.id), ("partner_id", "=", old.id)]).unlink()
        exists = Followers.search([("res_model", "=", "sale.order"), ("res_id", "=", sale.id), ("partner_id", "=", new.id)], limit=1)
        if not exists:
            subtype = self.env.ref("mail.mt_comment", raise_if_not_found=False)
            self.env["mail.followers"].create({
                "res_model": "sale.order",
                "res_id": sale.id,
                "partner_id": new.id,
                "subtype_ids": [(6, 0, subtype.ids if subtype else [])],
            })

    def action_apply(self):
        self.ensure_one()
        sale = self.sale_id.sudo()
        if not sale:
            raise UserError(_("No se encontró el pedido activo en el contexto."))
        if sale.state != "sale":
            raise UserError(_("Solo se permite cambiar el cliente en pedidos confirmados."))

        self._check_no_advance_payments(sale)
        self._check_no_accounting_done(sale)

        new_partner = self.new_partner_id
        if not new_partner:
            raise UserError(_("Seleccione el nuevo cliente."))

        old_partner = sale.partner_id
        old_invoice = sale.partner_invoice_id
        old_shipping = sale.partner_shipping_id

        sale.write({"partner_id": new_partner.id})

        if self.update_addresses:
            addrs = new_partner.address_get(['invoice', 'delivery']) or {}
            inv_id = addrs.get('invoice') or new_partner.id
            ship_id = addrs.get('delivery') or new_partner.id
            sale.write({"partner_invoice_id": inv_id, "partner_shipping_id": ship_id})

        if self.apply_billing_defaults:
            sale.write({
                "payment_term_id": new_partner.property_payment_term_id.id if new_partner.property_payment_term_id else False,
            })

        if self.recompute_taxes:
            partner = sale.partner_id
            delivery = sale.partner_shipping_id or partner
            FposM = self.env['account.fiscal.position'].with_company(sale.company_id)
            new_fpos = False
            if hasattr(FposM, 'get_fiscal_position'):
                try:
                    new_fpos = FposM.get_fiscal_position(partner=partner, delivery=delivery)
                except TypeError:
                    try:
                        new_fpos = FposM.get_fiscal_position(partner_id=partner.id, delivery_id=delivery.id)
                    except TypeError:
                        new_fpos = False
            if not new_fpos and hasattr(FposM, '_get_fiscal_position'):
                try:
                    new_fpos = FposM._get_fiscal_position(partner.id, delivery.id)
                except TypeError:
                    try:
                        new_fpos = FposM._get_fiscal_position(partner_id=partner.id, delivery_id=delivery.id)
                    except TypeError:
                        new_fpos = False
            sale.fiscal_position_id = (new_fpos or False) if isinstance(new_fpos, int) else (new_fpos.id if new_fpos else False)

        if self.use_partner_pricelist and new_partner.property_product_pricelist:
            sale.write({'pricelist_id': new_partner.property_product_pricelist.id})

        if self.use_partner_pricelist or self.recompute_prices:
            pl = sale.pricelist_id
            lines = sale.order_line.filtered(lambda l: not l.display_type)

            def _final_and_base(pricelist, line, order):
                price = None
                rule_id = False
                qty = line.product_uom_qty or 1.0
                if hasattr(pricelist, 'get_product_price_rule'):
                    price, rule_id = pricelist.get_product_price_rule(line.product_id, qty, order.partner_id)
                elif hasattr(pricelist, 'get_product_price'):
                    price = pricelist.get_product_price(line.product_id, qty, order.partner_id)
                elif hasattr(pricelist, 'price_get'):
                    price = pricelist.price_get(line.product_id.id, qty, partner=order.partner_id.id)[pricelist.id]
                base_price = None
                if rule_id:
                    item = self.env['product.pricelist.item'].browse(rule_id)
                    if item.compute_price in ('percentage', 'formula'):
                        if item.base == 'pricelist' and item.base_pricelist_id:
                            if hasattr(item.base_pricelist_id, 'get_product_price_rule'):
                                base_price, r2 = item.base_pricelist_id.get_product_price_rule(line.product_id, qty, order.partner_id)
                            elif hasattr(item.base_pricelist_id, 'get_product_price'):
                                base_price = item.base_pricelist_id.get_product_price(line.product_id, qty, order.partner_id)
                            elif hasattr(item.base_pricelist_id, 'price_get'):
                                base_price = item.base_pricelist_id.price_get(line.product_id.id, qty, partner=order.partner_id.id)[item.base_pricelist_id.id]
                        elif item.base == 'list_price':
                            base_price = float(line.product_id.price_compute('list_price', uom=line.product_uom, currency=order.currency_id).get(line.product_id.id) or 0.0)
                        elif item.base == 'standard_price':
                            base_price = float(line.product_id.price_compute('standard_price', uom=line.product_uom, currency=order.currency_id).get(line.product_id.id) or 0.0)
                if base_price is None:
                    base_price = float(line.product_id.price_compute('list_price', uom=line.product_uom, currency=order.currency_id).get(line.product_id.id) or 0.0)
                return price, base_price

            for line in lines:
                final_price, base_price = _final_and_base(pl, line, sale)
                if final_price is None:
                    final_price = base_price
                if self.force_breakdown_discount or pl.discount_policy == 'with_discount':
                    disc = 0.0
                    if base_price:
                        disc = max(0.0, (1.0 - (float(final_price) / base_price)) * 100.0)
                    line.write({'price_unit': base_price, 'discount': disc})
                else:
                    line.write({'price_unit': float(final_price), 'discount': 0.0})

            lines._compute_tax_id()
            lines._compute_amount()

        if self.recompute_taxes:
            sale.order_line._compute_tax_id()

        if self.update_proc_group and sale.procurement_group_id:
            sale.procurement_group_id.write({"partner_id": sale.partner_id.commercial_partner_id.id})

        if self.update_open_pickings:
            open_pickings = sale.picking_ids.filtered(lambda p: p.state not in ("done", "cancel"))
            target_partner_for_pickings = (sale.partner_shipping_id.id if self.update_addresses else sale.partner_id.id)
            for picking in open_pickings:
                picking.write({"partner_id": target_partner_for_pickings})
                picking.message_post(body=_("Partner actualizado por cambio de cliente en el pedido %s.") % sale.name)

        if self.update_followers:
            self._update_followers(sale, old_partner, new_partner)

        note_lines = [
            _("Cambio de cliente."),
            _("Cliente anterior: %s") % (old_partner.display_name,),
            _("Nuevo cliente: %s") % (new_partner.display_name,),
        ]
        if self.update_addresses:
            note_lines += [
                _("Factura: %s → %s") % (old_invoice.display_name or "-", sale.partner_invoice_id.display_name or "-"),
                _("Entrega: %s → %s") % (old_shipping.display_name or "-", sale.partner_shipping_id.display_name or "-"),
            ]
        if self.apply_billing_defaults:
            note_lines.append(_("Se aplicaron condiciones de pago del nuevo cliente."))
        if self.recompute_taxes:
            note_lines.append(_("Se recalculó la posición fiscal e impuestos."))
        if self.recompute_prices:
            note_lines.append(_("Se recalcularon precios y descuentos según la tarifa del pedido."))
        if self.use_partner_pricelist:
            note_lines.append(_("La tarifa del pedido se cambió a la del nuevo cliente."))
        if self.note_reason:
            note_lines.append(_("Motivo: %s") % self.note_reason)

        sale.message_post(body="<br/>".join(note_lines))
        return {"type": "ir.actions.act_window_close"}
