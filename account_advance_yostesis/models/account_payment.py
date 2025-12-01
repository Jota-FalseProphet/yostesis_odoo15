from odoo import api, fields, models


class AccountPayment(models.Model):
    _inherit = "account.payment"

    # Marca si el pago es un anticipo (cliente o proveedor).
    is_advance = fields.Boolean(readonly=True, copy=False)

    # ------------------------------------------------------------
    # LÍNEA DE CONTRAPARTIDA (normalmente 430/400)
    # ------------------------------------------------------------
    def _get_counterpart_move_line_vals(self, write_off_line_vals=None):
        """
        Línea de contrapartida (normalmente 430/400).

        Para anticipos de VENTA (cliente):
        - is_advance = True
        - SIN purchase_id (no viene de una compra)
        - Forzamos la cuenta 438xxxx (account_advance_customer_id).

        El sentido DEBE/HABER lo determina la lógica estándar de pagos:
        - En un cobro de cliente (inbound), la contrapartida va al HABER.
        """
        self.ensure_one()
        vals = super()._get_counterpart_move_line_vals(write_off_line_vals)

        # Consideramos anticipo de venta todo lo que sea anticipo y NO tenga purchase_id
        if (
            self.is_advance
            and not self.purchase_id
            and self.company_id.account_advance_customer_id
        ):
            # 438xxxxx (Anticipos de clientes)
            vals["account_id"] = self.company_id.account_advance_customer_id.id

        return vals

    # ------------------------------------------------------------
    # LÍNEA DE LIQUIDEZ (BANCO)
    # ------------------------------------------------------------
    def _get_liquidity_move_line_vals(self, amount):
        """
        Línea de liquidez (banco).

        Para anticipos de VENTA (cliente):
        - is_advance = True
        - SIN purchase_id
        - Intentamos usar 572002000 (Outstanding Receipts) como cuenta de liquidez.
        - Si no existe, caemos al suspense configurado.

        El sentido DEBE/HABER también lo marca la lógica estándar:
        - En un cobro de cliente (inbound), la liquidez va al DEBE.
        """
        self.ensure_one()
        vals = super()._get_liquidity_move_line_vals(amount)

        # Si no es anticipo, se deja el comportamiento estándar.
        if not self.is_advance:
            return vals

        company = self.company_id
        outstanding = False

        # Anticipo de VENTA (cliente): anticipo sin purchase_id
        if not self.purchase_id:
            outstanding = self.env["account.account"].search(
                [
                    ("code", "=", "572002000"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )

        if not outstanding:
            # Fallback: suspense global
            suspense = getattr(company, "account_journal_suspense_account_id", False)
            if not suspense:
                suspense = getattr(company, "account_journal_suspense_id", False)
                if not suspense:
                    Settings = self.env["res.config.settings"]
                    field = Settings._fields.get("account_journal_suspense_id")
                    param_name = getattr(field, "config_parameter", False) if field else False
                    if param_name:
                        icp = self.env["ir.config_parameter"].sudo()
                        suspense_id = icp.get_param(param_name)
                        if suspense_id:
                            suspense = self.env["account.account"].browse(int(suspense_id))
            outstanding = suspense

        if outstanding:
            vals["account_id"] = outstanding.id

        return vals

    # ------------------------------------------------------------
    # POST → AJUSTE FINO DE ANTICIPOS DE VENTA
    # ------------------------------------------------------------
    def action_post(self):
        """
        Después de postear el pago, corregimos asientos simples de anticipo de venta:

        Queremos que el asiento quede SIEMPRE así en un cobro de cliente:

            DEBE   572002000 (Outstanding Receipts)
            HABER  438xxxx   (Anticipos de clientes)

        La lógica estándar de account.payment ya genera el sentido correcto;
        aquí solo nos aseguramos de que las cuentas sean las correctas
        (438 / 572002000 o suspense).
        """
        res = super().action_post()
        self._fix_simple_sale_advance_entries()
        return res

    def _fix_simple_sale_advance_entries(self):
        """
        Ajusta pagos de anticipo de venta vinculados a un pedido de venta:

        - Nos aseguramos de que:
            * La línea de anticipo usa la cuenta 438xxxx (account_advance_customer_id).
            * La otra línea de contrapartida usa 572002000 (o suspense si no existe).

        No tocamos importes ni signos (DEBE/HABER), solo la cuenta contable
        de cada línea.
        """
        SaleOrder = self.env["sale.order"]
        Account = self.env["account.account"]

        for pay in self:
            # Solo tratamos anticipos de VENTA: anticipo sin purchase_id
            if not pay.is_advance:
                continue
            if pay.purchase_id:
                continue

            # Buscar pedido de venta vinculado a este pago
            sale = SaleOrder.search(
                [("account_payment_ids", "in", pay.id)],
                limit=1,
            )
            if not sale:
                continue

            move = pay.move_id
            if not move or move.state != "posted":
                continue

            company = move.company_id
            adv_account = company.account_advance_customer_id
            if not adv_account:
                continue

            # Línea de anticipo (438)
            adv_line = move.line_ids.filtered(
                lambda l: l.account_id.id == adv_account.id
            )[:1]

            # Si aún no hay línea 438, intentamos sustituir la 430 del cliente por 438
            if not adv_line:
                partner_recv_lines = move.line_ids.filtered(
                    lambda l: l.account_id.internal_type == "receivable"
                    and l.partner_id == pay.partner_id.commercial_partner_id
                )
                # Normalmente habrá una línea 430, pero si no, mejor no tocar
                if len(partner_recv_lines) != 1:
                    continue
                adv_line = partner_recv_lines[0]
                adv_line.with_context(
                    skip_account_move_synchronization=True
                ).write({"account_id": adv_account.id})

            # Vuelve a buscar, asegurando que adv_line es la 438
            adv_line = move.line_ids.filtered(
                lambda l: l.account_id.id == adv_account.id
            )[:1]
            if not adv_line:
                continue

            # El resto debería ser la línea de banco / suspense
            other_lines = move.line_ids.filtered(lambda l: l.id != adv_line.id)
            if len(other_lines) != 1:
                continue
            other_line = other_lines[0]

            # Cuenta 572002000 preferente
            outstanding = Account.search(
                [
                    ("code", "=", "572002000"),
                    ("company_id", "=", company.id),
                ],
                limit=1,
            )

            # Fallback: suspense
            if not outstanding:
                suspense = getattr(company, "account_journal_suspense_account_id", False)
                if not suspense:
                    suspense = getattr(company, "account_journal_suspense_id", False)
                    if not suspense:
                        Settings = self.env["res.config.settings"]
                        field = Settings._fields.get("account_journal_suspense_id")
                        param_name = getattr(field, "config_parameter", False) if field else False
                        if param_name:
                            icp = self.env["ir.config_parameter"].sudo()
                            suspense_id = self.env["ir.config_parameter"].sudo().get_param(param_name)
                            if suspense_id:
                                suspense = Account.browse(int(suspense_id))
                outstanding = suspense

            if not outstanding:
                continue

            # Si la otra línea ya está en la cuenta correcta, no hacemos nada.
            if other_line.account_id.id == outstanding.id:
                continue

            # Solo cambiamos la CUENTA de la otra línea, mantenemos sus débitos/créditos.
            other_line.with_context(
                skip_account_move_synchronization=True
            ).write({"account_id": outstanding.id})
