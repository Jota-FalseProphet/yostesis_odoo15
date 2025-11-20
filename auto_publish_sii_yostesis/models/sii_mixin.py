
from odoo import _, exceptions, fields, models

class SiiMixin(models.AbstractModel):
    _inherit = "sii.mixin"

    sii_test = fields.Boolean(string="Sii Test", help="Was send while on Test Mode", default=False, readonly=True)

    def _send_document_to_sii(self):
        for document in self.filtered(lambda i: i.state in self._get_valid_document_states()):
            document.sii_test = document.company_id.sii_test
        return super(SiiMixin, self)._send_document_to_sii()