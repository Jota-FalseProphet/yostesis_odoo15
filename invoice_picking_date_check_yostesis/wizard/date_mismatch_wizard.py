from odoo import models, fields


class InvoicePickingDateMismatchWizard(models.TransientModel):
    _name = 'invoice.picking.date.mismatch.wizard'
    _description = 'Wizard de discrepancia de fechas albarán-factura'

    move_ids = fields.Many2many('account.move')
    line_ids = fields.One2many(
        'invoice.picking.date.mismatch.line', 'wizard_id',
    )

    def action_confirm(self):
        self.ensure_one()
        self.move_ids.with_context(skip_picking_date_check=True).action_post()
        return {'type': 'ir.actions.act_window_close'}


class InvoicePickingDateMismatchLine(models.TransientModel):
    _name = 'invoice.picking.date.mismatch.line'
    _description = 'Línea de discrepancia de fechas albarán-factura'

    wizard_id = fields.Many2one(
        'invoice.picking.date.mismatch.wizard', ondelete='cascade',
    )
    product_id = fields.Many2one('product.product', string='Producto', readonly=True)
    picking_id = fields.Many2one('stock.picking', string='Albarán', readonly=True)
    date_done = fields.Datetime(string='Fecha Recepción', readonly=True)
    move_date = fields.Date(string='Fecha Contable', readonly=True)
