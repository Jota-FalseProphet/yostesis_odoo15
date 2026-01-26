from collections import defaultdict
from odoo import api, fields, models

class StockPicking(models.Model):
    _inherit = "stock.picking"

    pmx_operations_total_display = fields.Char(compute="_compute_pmx_operations_total_display")

    @api.depends("move_ids_without_package.product_uom_qty", "move_ids_without_package.product_uom", "move_ids_without_package.state")
    def _compute_pmx_operations_total_display(self):
        Uom = self.env["uom.uom"]
        for p in self:
            by_uom = defaultdict(float)
            for m in p.move_ids_without_package.filtered(lambda x: x.state != "cancel"):
                if m.product_uom and m.product_uom_qty:
                    by_uom[m.product_uom.id] += m.product_uom_qty

            if not by_uom:
                p.pmx_operations_total_display = "0"
                continue

            if len(by_uom) == 1:
                uom_id, qty = next(iter(by_uom.items()))
                uom = Uom.browse(uom_id)
                p.pmx_operations_total_display = f"{qty:g} {uom.name}"
            else:
                parts = []
                for uom_id in sorted(by_uom.keys()):
                    uom = Uom.browse(uom_id)
                    parts.append(f"{by_uom[uom_id]:g} {uom.name}")
                p.pmx_operations_total_display = " | ".join(parts)
