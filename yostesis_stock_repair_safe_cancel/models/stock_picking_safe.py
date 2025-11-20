# models/stock_picking.py
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class StockPicking(models.Model):
    _inherit = "stock.picking"

    is_broken_picking = fields.Boolean(
        compute="_compute_is_broken_picking",
        string="Albarán roto",
        store=False
    )

    @api.depends('move_lines.state', 'move_line_ids.qty_done')
    def _compute_is_broken_picking(self):
        for p in self:
            p.is_broken_picking = p._is_broken()

    def action_safe_back2draft(self):
        """
        Restaurar albarán:
        - Si hay moves en DONE → devolución automática + crear un NUEVO picking de reintento con las cantidades devueltas.
        - Si NO hay DONE → camino ligero: limpiar qty_done fantasma, cancelar no-done, volver a borrador, consolidar, reservar.
        """
        for p in self:
            done_moves = p.move_lines.filtered(lambda m: m.state == 'done')
            if done_moves:
                # Hace devolución y crea un picking nuevo con los movimientos a reprocesar
                p._auto_return_and_recreate_moves(done_moves, create_new_picking_on_return=True)
            else:
                p._safe_prepare_for_cancel()
                to_cancel = p.move_lines.filtered(lambda m: m.state not in ('done', 'cancel'))
                if to_cancel:
                    # Bandera para no chocar con guardas en stock.move._action_cancel()
                    to_cancel.with_context(from_safe_back2draft=True)._action_cancel()
                # Volver a borrador
                if hasattr(p, 'action_back_to_draft'):
                    p.action_back_to_draft()
                elif hasattr(p, 'action_set_draft'):
                    p.action_set_draft()
                else:
                    p.write({'state': 'draft'})
                p._consolidate_moves()
                try:
                    p.action_assign()
                except Exception:
                    pass
        return True

    def _auto_return_and_recreate_moves(self, done_moves, create_new_picking_on_return=True):
        """
        1) Crea un picking de devolución (invertido) por la qty hecha (respetando lotes).
        2) Crea movimientos a reprocesar:
           - Si create_new_picking_on_return=True → en un NUEVO picking "reintento".
           - Si False → en el propio picking (comportamiento anterior, puede ensuciar histórico).
        """
        self.ensure_one()
        if not done_moves:
            return True

        # === 1) Picking de devolución (usar picking_type de devolución y ubicaciones correctas) ===
        ret_type = self.picking_type_id.return_picking_type_id
        if not ret_type:
            raise UserError(_("El tipo de operación no tiene configurado un tipo de devolución."))

        # Origen/destino del picking de devolución
        ret_src = ret_type.default_location_src_id.id if ret_type.default_location_src_id else self.location_dest_id.id
        # Si hay subcontratación, tratar de usar ubicación del subcontratista como destino
        is_subcontract = any(getattr(m, 'is_subcontract', False) for m in done_moves)
        subc_loc = False
        if is_subcontract and hasattr(self.partner_id.with_company(self.company_id), 'property_stock_subcontractor'):
            subc_loc = self.partner_id.with_company(self.company_id).property_stock_subcontractor.id or False
        ret_dst = ret_type.default_location_dest_id.id if ret_type.default_location_dest_id else (subc_loc or self.location_id.id)

        ret_vals = {
            'picking_type_id': ret_type.id,
            'company_id': self.company_id.id,
            'partner_id': self.partner_id.id,
            'origin': (self.origin or self.name or '') + ' - RETURN (auto)',
            'location_id': ret_src,
            'location_dest_id': ret_dst,
        }
        ret_picking = self.env['stock.picking'].create(ret_vals)

        # === 2) Movimientos de devolución (invertidos) ===
        ret_moves = self.env['stock.move']
        ret_map = []  # (move_done, move_return)
        for m in done_moves:
            qty_done = sum(m.move_line_ids.mapped('qty_done')) or m.product_uom_qty
            if not qty_done:
                continue
            mv_vals = {
                'name': (m.name or m.product_id.display_name) + ' (RETURN)',
                'picking_id': ret_picking.id,
                'product_id': m.product_id.id,
                'product_uom': m.product_uom.id,
                'product_uom_qty': qty_done,
                'location_id': m.location_dest_id.id,  # invertimos
                'location_dest_id': m.location_id.id,
                'move_orig_ids': [(6, 0, [])],
                'move_dest_ids': [(6, 0, [])],
                'company_id': m.company_id.id,
            }
            if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                mv_vals['purchase_line_id'] = m.purchase_line_id.id
            ret_m = self.env['stock.move'].create(mv_vals)
            ret_moves |= ret_m
            ret_map.append((m, ret_m))

        if not ret_moves:
            raise UserError(_("No se pudieron crear movimientos de devolución (qty_done=0)."))

        # Confirmar (MRP/Subcontract puede explotar/cancelar otros moves; no debería tener qty_done)
        ret_moves._action_confirm()

        # === 3) Move lines de devolución respetando lotes ===
        for m, ret_m in ret_map:
            ml_done = m.move_line_ids.filtered(lambda l: l.qty_done)
            if ml_done:
                for ml in ml_done:
                    self.env['stock.move.line'].create({
                        'move_id': ret_m.id,
                        'picking_id': ret_picking.id,
                        'product_id': ml.product_id.id,
                        'location_id': ret_m.location_id.id,
                        'location_dest_id': ret_m.location_dest_id.id,
                        'product_uom_id': ml.product_uom_id.id,
                        'qty_done': ml.qty_done,
                        'lot_id': getattr(ml, 'lot_id', False) and ml.lot_id.id or False,
                        'lot_name': getattr(ml, 'lot_name', False) or False,
                        'package_id': getattr(ml, 'package_id', False) and ml.package_id.id or False,
                        'result_package_id': getattr(ml, 'result_package_id', False) and ml.result_package_id.id or False,
                    })
            else:
                self.env['stock.move.line'].create({
                    'move_id': ret_m.id,
                    'picking_id': ret_picking.id,
                    'product_id': ret_m.product_id.id,
                    'location_id': ret_m.location_id.id,
                    'location_dest_id': ret_m.location_dest_id.id,
                    'product_uom_id': ret_m.product_uom.id,
                    'qty_done': ret_m.product_uom_qty,
                })

        # Reservar (si aplica)
        try:
            ret_picking.action_assign()
        except Exception:
            pass

        # === 4) Validar devolución ===
        ret_picking.button_validate()

        # === 5) Recrear movimientos para re-procesar ===
        #     a) en un NUEVO picking (limpio), o
        #     b) en el mismo (opción legacy: puede ensuciar).
        target_picking = self
        if create_new_picking_on_return:
            new_vals = {
                'picking_type_id': self.picking_type_id.id,
                'company_id': self.company_id.id,
                'partner_id': self.partner_id.id,
                'origin': (self.origin or self.name or '') + ' - RETRY',
                'location_id': self.location_id.id,
                'location_dest_id': self.location_dest_id.id,
            }
            target_picking = self.env['stock.picking'].create(new_vals)

        new_moves = self.env['stock.move']
        for m in done_moves:
            qty_done = sum(m.move_line_ids.mapped('qty_done')) or m.product_uom_qty
            vals = {
                'picking_id': target_picking.id,
                'state': 'draft',
                'move_orig_ids': [(6, 0, [])],
                'move_dest_ids': [(6, 0, [])],
                'product_uom_qty': qty_done,
            }
            if hasattr(m, 'purchase_line_id') and m.purchase_line_id:
                vals['purchase_line_id'] = m.purchase_line_id.id
            new_moves |= m.copy(default=vals)

        if new_moves:
            new_moves._action_confirm()
            try:
                target_picking.action_assign()
            except Exception:
                pass

        return True

    def _safe_prepare_for_cancel(self):
        for p in self:
            if p.state == "done":
                raise UserError(_("No se puede volver a borrador un albarán finalizado."))
            if p._is_broken():
                p._repair_rescue()
            else:
                done_lines = p.move_line_ids.filtered(lambda l: l.qty_done)
                if done_lines:
                    done_lines.write({"qty_done": 0})
                    p.move_lines._recompute_state()
        return True

    def _is_broken(self):
        self.ensure_one()
        return bool(self.move_lines) and all(m.state == "cancel" for m in self.move_lines) and any(ml.qty_done > 0 for ml in self.move_line_ids)

    def _consolidate_moves(self):
        self.ensure_one()
        groups = {}
        to_unlink = self.env["stock.move"]
        for m in self.move_lines.filtered(lambda m: m.state in ("draft","confirmed","assigned","waiting","ready")):
            key = (m.product_id.id, m.product_uom.id, m.location_id.id, m.location_dest_id.id)
            if key in groups:
                k = groups[key]
                m.move_line_ids.write({"move_id": k.id})
                k.product_uom_qty += m.product_uom_qty
                to_unlink |= m
            else:
                groups[key] = m
        if to_unlink:
            to_unlink.unlink()
            self.move_lines._recompute_state()
        return True

    def _repair_rescue(self):
        self.ensure_one()
        done_lines = self.move_line_ids.filtered(lambda ml: ml.qty_done > 0 and ml.move_id.state == "cancel")
        if done_lines:
            done_lines.write({"qty_done": 0})
            self.move_lines._recompute_state()
        return {"new_moves": []}
