# -*- coding: utf-8 -*-
from odoo import models, _
from odoo.exceptions import UserError


class AccountVoucherWizard(models.TransientModel):
    _inherit = "account.voucher.wizard"

    def _prepare_payment_vals(self, sale):
        vals = super()._prepare_payment_vals(sale)

        company = sale.company_id

        # Campo configurado en la compañía
        account_438 = company.account_advance_customer_id

        # autodetecta la cuenta 438 si no está configurada
        if not account_438:
            account_438 = self.env["account.account"].search(
                [
                    ("company_id", "=", company.id),
                    ("code", "like", "438%"),
                    ("deprecated", "=", False),
                ],
                limit=1,
            )

        # si por un causal no se ha encontrado una cuenta 438
        # lanza un error al usuario
        # para que la configure en la compañía
        if not account_438:
            raise UserError(
                _(
                    "No se ha encontrado ninguna cuenta 438 activa en el plan "
                    "contable de la empresa '%s'.\n\n"
                    "• Añádela en Contabilidad ▸ Plan contable, o\n"
                    "• Configúrala explícitamente en Ajustes ▸ Compañía "
                    "en el campo 'Cuenta de anticipos de clientes'."
                )
                % company.display_name
            )

        # Usamos la 438 detectada para la línea 'receivable'
        vals["destination_account_id"] = account_438.id
        return vals
