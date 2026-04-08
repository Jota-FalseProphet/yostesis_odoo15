from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    # Patch 1: store=True para que origin_sale y sale_line_id sean buscables/agrupables.
    # Sin esto, el backend lanza "Non-stored field mrp.production.sale_line_id cannot be searched."

    origin_sale = fields.Many2one(
        comodel_name="sale.order",
        string="Origin Sale",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Origin Sale Line",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    # Patch 2: Override search_origin_sale para anadir un paso 4 que siga la cadena
    # de moves hacia adelante (move_finished_ids -> move_dest_ids) hasta encontrar
    # una OF consumidora que conozca su venta de origen.
    #
    # Caso que resuelve:
    #   PV02251 -> OF-28850 (producto final)
    #     raw: ANOD01 <- VAL/ENTRADA/03089 <- VAL/SBC/01336 (subcontratacion)
    #       raw: MEC01 <- VAL/OUT-SUB/01185 <- OF-28855 (OF componente)
    #
    # OF-28855 no encuentra la venta por las 3 rutas originales porque:
    #   1) su procurement group no tiene sale_id
    #   2) sus raw moves no tienen move_orig_ids (ALU01 viene de stock)
    #   3) _get_sources() devuelve VAL/SBC/01336 con origin=False (dead-end)
    #
    # El paso 4 sigue: OF-28855.finished -> OUT-SUB -> SBC.raw -> SBC.finished ->
    #   ENTRADA -> OF-28850.raw -> OF-28850 tiene origin_sale -> PV02251

    def search_origin_sale(self):
        result = super().search_origin_sale()
        if result[0]:
            return result

        # Paso 4: Seguir el producto terminado hacia adelante por la cadena de supply
        # hasta encontrar una OF consumidora que conozca su venta de origen.
        try:
            moves_to_check = self.move_finished_ids.move_dest_ids
            visited_move_ids = set()
            max_depth = 50
            depth = 0
            while moves_to_check and depth < max_depth:
                depth += 1
                next_moves = self.env['stock.move']
                for move in moves_to_check:
                    if move.id in visited_move_ids:
                        continue
                    visited_move_ids.add(move.id)
                    consuming_mo = move.raw_material_production_id
                    if consuming_mo and consuming_mo.id != self.id:
                        mo_result = consuming_mo.search_origin_sale()
                        if mo_result[0]:
                            return mo_result
                    next_moves |= move.move_dest_ids
                moves_to_check = next_moves
        except Exception as e:
            _logger.error('Error in search_origin_sale forward chain: %s', e)

        return False, False

    # Patch 3: Override _compute_origin_sale para anadir dependencias de la cadena forward.
    # Sin esto, el stored compute no se re-dispara cuando se enlazan los moves downstream.
    @api.depends(
        'procurement_group_id.mrp_production_ids.move_dest_ids.group_id',
        'procurement_group_id.mrp_production_ids.move_dest_ids.group_id.stock_move_ids',
        'procurement_group_id.mrp_production_ids.move_dest_ids.group_id.mrp_production_ids',
        'procurement_group_id.stock_move_ids.move_dest_ids.group_id.mrp_production_ids',
        'origin',
        'move_finished_ids.move_dest_ids.raw_material_production_id',
    )
    def _compute_origin_sale(self):
        for record in self:
            sale_id, sale_line_id = record.search_origin_sale()
            record.origin_sale = sale_id
            record.sale_line_id = sale_line_id

    def action_confirm(self):
        result = super().action_confirm()
        # At this point ALL moves (raw + finished) are created and linked.
        # _run_manufacture calls action_confirm AFTER creating moves (line 21),
        # so the full forward chain exists. Force recompute + flush to DB now.
        mos_empty = self.filtered(lambda m: not m.origin_sale)
        if mos_empty:
            _logger.info(
                'Recomputing origin_sale on confirm for %d MOs: %s',
                len(mos_empty),
                mos_empty.mapped('name'),
            )
            mos_empty._compute_origin_sale()
            mos_empty.flush(['origin_sale', 'sale_line_id'])
        return result
