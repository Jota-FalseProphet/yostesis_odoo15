from odoo import models, fields

#campos para configurar si se requieren impuestos en líneas de factura
class ResCompany(models.Model):
    _inherit = "res.company"

    invoice_line_tax_required = fields.Boolean(
        string="Impuestos obligatorios en líneas de factura",
        default=False,
    )

class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    invoice_line_tax_required = fields.Boolean(
        string="Impuestos obligatorios en líneas de factura",
        related="company_id.invoice_line_tax_required",
        readonly=False,
    )
