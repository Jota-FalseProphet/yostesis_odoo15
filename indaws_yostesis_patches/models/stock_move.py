from odoo import api, models
import logging

_logger = logging.getLogger(__name__)


class StockMove(models.Model):
    _inherit = "stock.move"

    @api.model_create_multi
    def create(self, vals_list):
        moves = super().create(vals_list)
        # Safety net: recompute origin_sale when finished moves are created.
        # The main recompute happens in action_confirm(), but this catches
        # edge cases where moves are created outside _run_manufacture.
        finished_mos = moves.filtered('production_id').mapped('production_id')
        mos_empty = finished_mos.filtered(lambda m: not m.origin_sale)
        if mos_empty:
            mos_empty._compute_origin_sale()
            mos_empty.flush(['origin_sale', 'sale_line_id'])
        return moves

    def write(self, vals):
        res = super().write(vals)
        if 'move_dest_ids' in vals or 'move_orig_ids' in vals:
            self._trigger_origin_sale_recompute()
        return res

    def _trigger_origin_sale_recompute(self):
        """Recompute origin_sale on MOs when move links change.

        When move_dest_ids changes on a finished move (e.g. line 177 of
        _subcontracted_produce links SBC finished → ENTRADA), we recompute
        the MO's origin_sale.  If it gets a value, we also propagate to
        upstream MOs that feed into this one (the component OFs like MECNOG05)
        because their forward chain now reaches a known sale order.
        """
        mos = self.filtered('production_id').mapped('production_id')
        mos |= self.filtered('raw_material_production_id').mapped(
            'raw_material_production_id'
        )
        mos_empty = mos.filtered(lambda m: not m.origin_sale)
        if mos_empty:
            _logger.info(
                'Recomputing origin_sale for %d MOs after link change: %s',
                len(mos_empty),
                mos_empty.mapped('name'),
            )
            mos_empty._compute_origin_sale()
            mos_empty.flush(['origin_sale', 'sale_line_id'])
            # Propagate: find upstream MOs (component OFs) whose forward chain
            # now reaches this MO.  Walk backwards through move_orig_ids until
            # we find moves with production_id (finished moves of upstream OFs).
            # Chain: upstream OF finished → OUT-SUB → SBC raw
            newly_filled = mos_empty.filtered(lambda m: m.origin_sale)
            if newly_filled:
                upstream_mos = self.env['mrp.production']
                for mo in newly_filled:
                    moves = mo.move_raw_ids.move_orig_ids
                    visited = set()
                    for _depth in range(5):
                        for m in moves:
                            if m.production_id:
                                upstream_mos |= m.production_id
                        new_moves = moves.move_orig_ids
                        new_ids = set(new_moves.ids) - visited
                        if not new_ids:
                            break
                        visited |= new_ids
                        moves = new_moves
                upstream_empty = upstream_mos.filtered(
                    lambda m: not m.origin_sale
                )
                if upstream_empty:
                    _logger.info(
                        'Propagating origin_sale to %d upstream MOs: %s',
                        len(upstream_empty),
                        upstream_empty.mapped('name'),
                    )
                    upstream_empty._compute_origin_sale()
                    upstream_empty.flush(['origin_sale', 'sale_line_id'])
