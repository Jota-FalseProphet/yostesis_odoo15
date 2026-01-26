from odoo import models, api, fields, _
from odoo.exceptions import ValidationError

class AccountMoveLine(models.Model):
    _inherit = "account.move.line"

    company_invoice_line_tax_required = fields.Boolean(
        related="move_id.company_id.invoice_line_tax_required",
        readonly=True,
    )
    
    # constraint para asegurar que todas las líneas de factura tengan al menos un impuesto asignado
    @api.constrains("tax_ids", "display_type", "move_id")
    def _check_invoice_line_taxes_required(self):
        for line in self:
            move = line.move_id
            if not move:
                continue

            if not move.company_id.invoice_line_tax_required:
                continue

            if line.display_type or line.exclude_from_invoice_tab:
                continue

            if move.move_type not in ("out_invoice", "out_refund", "in_invoice", "in_refund"):
                continue

            if not line.tax_ids:
                raise ValidationError(
                    _("All invoice lines must have at least one tax (company setting enabled).")
                )
