from odoo import models, fields


class AccountMove(models.Model):
    _inherit = "account.move"

    def action_post(self):
        if self._context.get('skip_picking_date_check'):
            return super().action_post()

        mismatches = []
        moves_with_mismatch = self.env['account.move']

        for move in self.filtered(lambda m: m.move_type == 'in_invoice' and m.state == 'draft'):
            move_mismatches = move._get_picking_date_mismatches()
            if move_mismatches:
                mismatches.extend(move_mismatches)
                moves_with_mismatch |= move

        if not mismatches:
            return super().action_post()

        moves_without_mismatch = self - moves_with_mismatch
        if moves_without_mismatch:
            moves_without_mismatch.with_context(skip_picking_date_check=True).action_post()

        wizard = self.env['invoice.picking.date.mismatch.wizard'].create({
            'move_ids': [(6, 0, moves_with_mismatch.ids)],
            'line_ids': [(0, 0, vals) for vals in mismatches],
        })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Discrepancia de fechas',
            'res_model': 'invoice.picking.date.mismatch.wizard',
            'res_id': wizard.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _get_picking_date_mismatches(self):
        self.ensure_one()
        mismatches = []
        seen = set()

        for line in self.invoice_line_ids.filtered(lambda l: l.purchase_line_id):
            pickings = line.purchase_line_id.move_ids.picking_id.filtered(
                lambda p: p.state == 'done' and p.date_done
            )
            for picking in pickings:
                picking_date = fields.Date.to_date(picking.date_done)
                if (picking_date.month, picking_date.year) != (self.date.month, self.date.year):
                    key = (line.product_id.id, picking.id)
                    if key not in seen:
                        seen.add(key)
                        mismatches.append({
                            'product_id': line.product_id.id,
                            'picking_id': picking.id,
                            'date_done': picking.date_done,
                            'move_date': self.date,
                        })

        return mismatches
