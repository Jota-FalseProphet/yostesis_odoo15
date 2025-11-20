# -*- coding: utf-8 -*-
from odoo import api, models, _
from odoo.modules.registry import Registry


class AccountMove(models.Model):
    _inherit = "account.move"

    def _cancel_invoice_to_sii(self):
            for invoice in self.filtered(lambda i: i.state in ["cancel"]):
                serv = invoice._connect_sii(invoice.move_type)
                # header = invoice._get_sii_header(cancellation=True)
                header = invoice._get_sii_header(True)
                inv_vals = {
                    "sii_send_failed": True,
                    "sii_send_error": False,
                }
                try:
                    inv_dict = invoice._get_cancel_sii_invoice_dict()
                    if invoice.move_type in ["out_invoice", "out_refund"]:
                        res = serv.AnulacionLRFacturasEmitidas(header, inv_dict)
                    else:
                        res = serv.AnulacionLRFacturasRecibidas(header, inv_dict)
                    # TODO Facturas intracomunitarias 66 RIVA
                    # elif invoice.fiscal_position_id.id == self.env.ref(
                    #     'account.fp_intra').id:
                    #     res = serv.AnulacionLRDetOperacionIntracomunitaria(
                    #         header, invoices)
                    inv_vals["sii_return"] = res
                    if res["EstadoEnvio"] == "Correcto":
                        inv_vals.update(
                            {
                                "sii_state": "cancelled",
                                "sii_csv": res["CSV"],
                                "sii_send_failed": False,
                            }
                        )
                    res_line = res["RespuestaLinea"][0]
                    if res_line["CodigoErrorRegistro"]:
                        inv_vals["sii_send_error"] = "{} | {}".format(
                            str(res_line["CodigoErrorRegistro"]),
                            str(res_line["DescripcionErrorRegistro"])[:60],
                        )
                    invoice.write(inv_vals)
                except Exception as fault:
                    new_cr = Registry(self.env.cr.dbname).cursor()
                    env = api.Environment(new_cr, self.env.uid, self.env.context)
                    invoice = env["account.move"].browse(invoice.id)
                    inv_vals.update(
                        {
                            "sii_send_failed": True,
                            "sii_send_error": repr(fault)[:60],
                            "sii_return": repr(fault),
                        }
                    )
                    invoice.write(inv_vals)
                    new_cr.commit()
                    new_cr.close()
                    raise
