from odoo import models


class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, **kwargs):
        body = kwargs.get('body', '') or ''

        if self._name in ['purchase.request', 'stock.picking']:
            is_receipt_notification = (
                'Receipt confirmation' in body
                or 'han sido recibidos' in body
            )
            if is_receipt_notification:
                kwargs['notify'] = False
                kwargs['partner_ids'] = []

        return super().message_post(**kwargs)
