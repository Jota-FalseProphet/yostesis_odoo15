from odoo import models
import logging

_logger = logging.getLogger(__name__)


class StockPicking(models.Model):
    _inherit = "stock.picking"

    def _action_done(self):
        result = super()._action_done()
        self._recompute_mos_origin_sale()
        return result

    def _subcontracted_produce(self, subcontract_details):
        """After subcontract MOs are produced/linked, the full move graph
        from upstream component MOs (e.g. PUL polishing OFs) down to the
        SO line exists. Recompute origin on every connected MO so they
        get the correct sale_line_id from the move graph (otherwise the
        compute may have run earlier with an incomplete chain and fallen
        back to name-matching, picking the wrong SO line when the SO has
        several similar variants)."""
        result = super()._subcontracted_produce(subcontract_details)
        try:
            self._recompute_mos_origin_sale(force=True)
        except Exception:
            _logger.exception('Error recomputing origin after _subcontracted_produce')
        return result

    def _recompute_mos_origin_sale(self, force=False):
        """After receipt validation, recompute origin_sale for connected MOs.

        At this point _subcontracted_produce() has already run, so the full
        chain of MOs, moves, and links is established.  We walk the move
        graph to find every MO connected to this picking, then recompute
        any that still lack an origin_sale.
        """
        all_mos = self.env['mrp.production']
        visited = set()
        moves = self.move_lines

        for _depth in range(10):
            next_moves = self.env['stock.move']
            for m in moves:
                if m.id in visited:
                    continue
                visited.add(m.id)
                all_mos |= m.production_id
                all_mos |= m.raw_material_production_id
                next_moves |= m.move_dest_ids | m.move_orig_ids
            new_ids = set(next_moves.ids) - visited
            if not new_ids:
                break
            moves = self.env['stock.move'].browse(list(new_ids))

        # Walk deeper from found MOs to reach upstream component MOs.
        # Chain: SBC raw -> OUT-SUB (no production_id) -> OF finished (has it)
        extra_mos = self.env['mrp.production']
        for mo in all_mos:
            # Upstream: walk raw move origins until we find production_id
            moves_up = mo.move_raw_ids.move_orig_ids
            seen = set()
            for _d in range(5):
                for m in moves_up:
                    if m.production_id:
                        extra_mos |= m.production_id
                new = moves_up.move_orig_ids
                new_ids = set(new.ids) - seen
                if not new_ids:
                    break
                seen |= new_ids
                moves_up = new
            # Downstream: walk finished move dests
            for dest in mo.move_finished_ids.move_dest_ids:
                if dest.raw_material_production_id:
                    extra_mos |= dest.raw_material_production_id
        all_mos |= extra_mos

        if force:
            empty = all_mos.filtered(lambda m: m.state != 'cancel')
        else:
            empty = all_mos.filtered(
                lambda m: m.state != 'cancel' and not m.origin_sale and not m.origin_purchase_id
            )
        if empty:
            _logger.info(
                'Recomputing origin for %d MOs after receipt: %s',
                len(empty),
                empty.mapped('name'),
            )
            empty._compute_origin_sale()
            empty.flush([
                'origin_sale', 'origin_product_id', 'origin_production_id',
                'sale_line_id', 'origin_purchase_id', 'origin_purchase_line_id',
                'display_origin', 'display_origin_name',
            ])
