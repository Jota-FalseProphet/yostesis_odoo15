# models/stock_move.py
from odoo import models, _
from odoo.exceptions import UserError

class StockMove(models.Model):
    _inherit = "stock.move"

    def _in_safe_restore_flow(self):
        return bool(self.env.context.get('from_safe_back2draft'))

    def _action_cancel(self):
        if not self._in_safe_restore_flow():
            bad = self.filtered(lambda m: any(l.qty_done for l in m.move_line_ids))
            if bad:
                raise UserError(_("No se pueden cancelar movimientos con operaciones realizadas (qty_done>0). Use 'Restaurar albarán'."))
        # Nunca cancelar moves en done (core lo prohíbe, mantenemos mensaje claro)
        done_moves = self.filtered(lambda m: m.state == 'done')
        if done_moves:
            raise UserError(_("Hay movimientos en estado Hecho. Cree una devolución para revertirlos antes de restaurar."))
        return super(StockMove, self.with_context(allow_direct_cancel=True))._action_cancel()

    def write(self, vals):
        if vals.get("state") == "cancel" and not (self.env.context.get("allow_direct_cancel") or self._in_safe_restore_flow()):
            raise UserError(_("Use _action_cancel() para cancelar."))
        return super().write(vals)
