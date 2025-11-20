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
    
    # def _get_sii_identifier(self):
    #     res = super()._get_sii_identifier()
    #     if "IDOtro" not in res:
    #         return res

    #     country = self._get_sii_country_code()
    #     otro = res["IDOtro"]

    #     # aseguramos CodigoPais
    #     otro["CodigoPais"] = country

    #     # si el partner trae IDType 06 lo respetamos;
    #     # quitamos prefijo NO si apareciera por error
    #     if otro.get("IDType") == "06" and otro["ID"].upper().startswith(country):
    #         otro["ID"] = otro["ID"][len(country):]

    #     return res



