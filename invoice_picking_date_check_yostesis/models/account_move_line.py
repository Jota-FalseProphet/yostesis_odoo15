from odoo import api, fields, models


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    picking_date_done = fields.Date(
        string='Fecha Recepción',
        compute='_compute_picking_date_done',
    )

    @api.depends('purchase_line_id.move_ids.picking_id.date_done')
    def _compute_picking_date_done(self):
        for line in self:
            if not line.purchase_line_id:
                line.picking_date_done = False
                continue
            done_moves = line.purchase_line_id.move_ids.filtered(
                lambda m: m.state == 'done' and m.picking_id.date_done
            )
            if done_moves:
                dates = done_moves.mapped('picking_id.date_done')
                line.picking_date_done = max(dates).date()
            else:
                line.picking_date_done = False
