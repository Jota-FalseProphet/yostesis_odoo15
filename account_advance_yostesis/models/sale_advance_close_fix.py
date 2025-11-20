# -*- coding: utf-8 -*-
from odoo import models

class AccountVoucherWizard(models.TransientModel):
    _inherit = 'account.voucher.wizard'  # del módulo OCA

    def make_advance_payment(self):
        """
        Reutiliza la lógica del OCA (crea y postea account.payment, etc.)
        y luego sanea la acción final por si algún módulo inyecta 'context'
        en el act_window_close, lo que genera WARNING en web.controllers.
        """
        res = super().make_advance_payment()
        if isinstance(res, dict) and res.get('type') == 'ir.actions.act_window_close':
            # eliminar cualquier 'context' u otras llaves custom
            res.pop('context', None)
            res.pop('params', None)
        return res
