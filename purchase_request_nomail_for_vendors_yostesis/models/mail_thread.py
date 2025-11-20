import logging
from odoo import models

_logger = logging.getLogger(__name__)

class MailThread(models.AbstractModel):
    _inherit = 'mail.thread'

    def message_post(self, **kwargs):
        self.ensure_one()

        body = kwargs.get('body', '') or ''
        model_blocked = self._name in ['purchase.request', 'stock.picking']
        is_receipt_notification = (
            'Receipt confirmation' in body
            or 'han sido recibidos' in body
        )

        _logger.info("[DEBUG PATCH] message_post called on model: %s", self._name)
        _logger.info("[DEBUG PATCH] body: %s", body)

        if model_blocked and is_receipt_notification:
            _logger.warning("[PATCH ACTIVE] Blocking email notification on %s (ID %s)", self._name, self.id)
            kwargs['notify'] = False
            kwargs['partner_ids'] = [] 

        return super().message_post(**kwargs)
