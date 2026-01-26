# auto_publish_sii_yostesis/models/sii_mixin_patch.py
from odoo import models

class SiiMixinPatch(models.AbstractModel):
    _inherit = "sii.mixin"

    def _get_sii_header(self, tipo_comunicacion):
        return super()._get_sii_header(tipo_comunicacion)

    def _get_sii_out_invoice_dict(self):
        self.ensure_one()
        inv_dict = super()._get_sii_out_invoice_dict()

        codigo = self.company_id.sii_tipo_desglose or '01'

        fac = inv_dict.setdefault('FacturaExpedida', {})
        fac.setdefault('DesgloseFactura', {})['DesgloseTipoOperacion'] = codigo

        return inv_dict

    def _get_sii_in_invoice_dict(self):
        self.ensure_one()
        inv_dict = super()._get_sii_in_invoice_dict()

        codigo = self.company_id.sii_tipo_desglose or '01'
        fac = inv_dict.setdefault('FacturaRecibida', {})
        fac.setdefault('DesgloseFactura', {})['DesgloseTipoOperacion'] = codigo

        return inv_dict
