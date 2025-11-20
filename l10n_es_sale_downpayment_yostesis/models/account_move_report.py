# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.tools import float_compare
from odoo.tools.misc import format_date


class AccountMove(models.Model):
    _inherit = 'account.move'

    def _pmx_candidate_downpayment_invoices(self):
        self.ensure_one()
        domain = [
            ('move_type', '=', 'out_invoice'),
            ('state', '=', 'posted'),
            ('id', '!=', self.id),
            ('partner_id', '=', self.partner_id.id),
        ]
        if self.invoice_origin:
            domain.append(('invoice_origin', 'ilike', self.invoice_origin))
        others = self.search(domain, order='invoice_date asc, id asc')

        def is_downpayment(inv):
            try:
                if hasattr(inv, '_is_downpayment_invoice') and inv._is_downpayment_invoice():
                    return True
            except Exception:
                pass
            if any(inv.invoice_line_ids.mapped('sale_line_ids.is_downpayment')):
                return True
            names = ' '.join((inv.invoice_line_ids.mapped('name') or [])).lower()
            return ('anticipo' in names) or ('down payment' in names)

        return others.filtered(is_downpayment)

    # === MATCH de la línea de deducción con su factura de anticipo ===
    def _pmx_dp_invoice_for_line(self, line):
        """Devuelve la factura de anticipo asociada a UNA LÍNEA DE DEDUCCIÓN."""
        self.ensure_one()
        try:
            if not line or line.move_id != self or line.display_type:
                return False

            name_l = (line.name or '').lower()
            is_deduction = (
                (line.quantity and line.quantity < 0)
                or (line.price_total and line.price_total < 0)
                or ('anticipo' in name_l) or ('down payment' in name_l)
            )
            if not is_deduction:
                return False

            # 1) Coincidencia por sale_line_ids (SIN 'balance')
            if line.sale_line_ids:
                aml_domain = [
                    ('sale_line_ids', 'in', line.sale_line_ids.ids),
                    ('move_id.move_type', '=', 'out_invoice'),
                    ('move_id.state', '=', 'posted'),
                    ('move_id.id', '!=', self.id),
                    ('display_type', '=', False),
                ]
                amls = self.env['account.move.line'].search(aml_domain)
                if amls:
                    candidates = []
                    target = abs(line.price_subtotal)  # comparamos base imponible
                    cur = self.currency_id
                    company = self.company_id

                    for mv in amls.mapped('move_id'):
                        rows = amls.filtered(lambda a: a.move_id == mv)
                        # Intersección de sale_line_ids
                        lsl = set(line.sale_line_ids.ids)
                        asl = set(sum((r.sale_line_ids.ids for r in rows), []))
                        common = len(lsl & asl)
                        # Suma base imponible de esas filas
                        sum_sub = sum(r.price_subtotal for r in rows)
                        # Convertir si hace falta
                        if mv.currency_id != cur:
                            sum_conv = mv.currency_id._convert(
                                sum_sub, cur, company, mv.invoice_date or fields.Date.context_today(self)
                            )
                        else:
                            sum_conv = sum_sub
                        is_match = cur.is_zero(sum_conv - target)
                        # Criterio: +common, importe que cuadra, fecha más reciente, id
                        key = (-common, 0 if is_match else 1,
                               (mv.invoice_date or mv.date or fields.Date.today()), mv.id)
                        candidates.append((key, mv))

                    if candidates:
                        candidates.sort(key=lambda x: x[0])
                        return candidates[0][1]

            # 2) Fallback por partner/origen y casando base imponible total
            candidates = self._pmx_candidate_downpayment_invoices()
            if candidates:
                target = abs(line.price_subtotal)
                cur = self.currency_id
                company = self.company_id
                best = None
                best_key = None
                for mv in candidates:
                    amt = mv.amount_untaxed
                    if mv.currency_id != cur:
                        amt = mv.currency_id._convert(
                            amt, cur, company, mv.invoice_date or fields.Date.context_today(self)
                        )
                    delta = abs(amt - target)
                    key = (0 if cur.is_zero(delta) else 1, delta,
                           mv.invoice_date or mv.date or fields.Date.today(), mv.id)
                    if best_key is None or key < best_key:
                        best_key, best = key, mv
                return best

            return False
        except Exception:
            return False

    def _pmx_is_dp_deduction_line(self, line):
        """True si la línea descuenta un anticipo (negativa o etiquetada)."""
        self.ensure_one()
        if not line or line.move_id != self or line.display_type:
            return False
        name_l = (line.name or '').lower()
        return (
            (line.quantity and line.quantity < 0)
            or (line.price_total and line.price_total < 0)
            or ('anticipo' in name_l) or ('down payment' in name_l)
        )

    # === 438 de la compañía ===
    def _pmx_acc438(self, company):
        """Cuenta de anticipos (438) configurada o detectada por código."""
        acc = getattr(company, 'account_advance_customer_id', False)
        if acc:
            return acc
        return self.env['account.account'].with_company(company).search([
            ('company_id', '=', company.id),
            ('code', '=like', '438%'),
            ('deprecated', '=', False),
        ], limit=1, order='code')

    # === Fecha de pago real del anticipo vía conciliación en 438 ↔ banco/caja ===
    def _pmx_dp_payment_date_via_438(self, move):
        """Última fecha de pago REAL del anticipo 'move' mirando reconciliaciones en 438
        contra asientos de diarios bank/cash (flujo manual de anticipo)."""
        try:
            acc438 = self._pmx_acc438(move.company_id)
            if not acc438:
                return False
            dates = []
            lines_438 = move.line_ids.filtered(
                lambda l: not l.display_type and l.account_id.id == acc438.id
            )
            for l in lines_438:
                parts = l.matched_debit_ids | l.matched_credit_ids  # account.partial.reconcile
                for pr in parts:
                    other_line = pr.debit_move_id if pr.credit_move_id == l else pr.credit_move_id
                    om = other_line.move_id
                    # En tu wizard, el apunte de cobro es move_type='entry' y journal.type ∈ ('bank','cash')
                    if getattr(om.journal_id, 'type', None) in ('bank', 'cash'):
                        dates.append(om.date or other_line.date)
            return max(dates) if dates else False
        except Exception:
            return False

    # === Fecha de pago real genérica (payment / bank-cash) por si existiera ===
    def _pmx_move_payment_date_only(self, move):
        """Última fecha de PAGO REAL aplicada a 'move':
        - account.payment (payment_id / account_payment_id) o
        - asiento en diario Bank/Cash (journal_id.type in ('bank','cash')).
        Ignora conciliaciones con otras facturas/notas."""
        try:
            pay_dates = []

            # 1) JSON del reporte: 'payment_id' / 'account_payment_id' o 'move_id' bancario
            vals = move.sudo()._get_reconciled_info_JSON_values() or []
            for v in vals:
                pid = v.get('payment_id') or v.get('account_payment_id')
                if pid:
                    pay = self.env['account.payment'].sudo().browse(pid)
                    d = pay.payment_date or pay.date or v.get('date')
                    d = fields.Date.to_date(d) if d else False
                    if d:
                        pay_dates.append(d)
                    continue
                mid = v.get('move_id')
                if mid:
                    om = self.env['account.move'].sudo().browse(mid)
                    if om and (om.payment_id or getattr(om.journal_id, 'type', None) in ('bank', 'cash')):
                        d = fields.Date.to_date(om.date) if om.date else False
                        if d:
                            pay_dates.append(d)

            if pay_dates:
                return max(pay_dates)

            # 2) Fallback: receivable/payable aceptando SOLO pagos reales
            plines = move.line_ids.filtered(
                lambda l: (getattr(l, 'account_internal_type', None) in ('receivable', 'payable')) or
                          (getattr(l.account_id, 'account_type', None) in ('asset_receivable', 'liability_payable'))
            )
            for line in plines:
                parts = line.matched_debit_ids | line.matched_credit_ids
                for pr in parts:
                    other_line = pr.debit_move_id if pr.credit_move_id == line else pr.credit_move_id
                    om = other_line.move_id
                    if om.payment_id or getattr(om.journal_id, 'type', None) in ('bank', 'cash'):
                        d = om.date or other_line.date
                        d = fields.Date.to_date(d) if d else False
                        if d:
                            pay_dates.append(d)

            return max(pay_dates) if pay_dates else False
        except Exception:
            return False

    def _pmx_downpayment_label_for_line(self, line):
        """Label con referencia + fecha del pago del anticipo (vía 438; fallback pagos reales)."""
        try:
            move = self._pmx_dp_invoice_for_line(line)
            if not move:
                return False

            # 1) Tu caso principal: pago manual por asiento de banco/caja conciliado en 438
            pay_date = self._pmx_dp_payment_date_via_438(move)

            # 2) Fallback: por si existiera un payment / asiento bancario detectado por el JSON
            if not pay_date:
                pay_date = self._pmx_move_payment_date_only(move)

            if pay_date:
                return _("Pago anticipado de la factura: %(name)s — pagada el %(date)s") % {
                    'name': move.name,
                    'date': format_date(self.env, fields.Date.to_date(pay_date)),
                }
            return _("Pago anticipado de la factura: %s") % move.name
        except Exception:
            return False

    def _pmx_dp_amount_for_line(self, line):
        """Importe del anticipo aplicado (total con impuestos, valor absoluto)."""
        self.ensure_one()
        if not line or line.move_id != self or line.display_type:
            return 0.0
        return abs(line.price_total or 0.0)

    def _pmx_show_qty_as_integer(self, line):
        """Muestra cantidad como entero y sin UoM si la UoM redondea a 1 (p.ej. 'Unidades')."""
        self.ensure_one()
        if not line or line.display_type:
            return False
        uom = line.product_uom_id
        return bool(uom and float_compare(uom.rounding or 0.0, 1.0, precision_digits=6) >= 0)
