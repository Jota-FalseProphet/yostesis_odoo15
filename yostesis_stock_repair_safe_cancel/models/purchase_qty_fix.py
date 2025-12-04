from odoo import api, models


class PurchaseOrderLine(models.Model):
    _inherit = "purchase.order.line"

    def _fix_qty_received_method_if_needed(self):
        for line in self:
            if (
                not line.display_type
                and line.product_id
                and line.product_id.type in ("product", "consu")
                and not line.qty_received_method
            ):
                line.qty_received_method = "stock_moves"

    @api.model
    def create(self, vals_list):
        lines = super().create(vals_list)
        lines._fix_qty_received_method_if_needed()
        return lines

    def write(self, vals):
        res = super().write(vals)
        self._fix_qty_received_method_if_needed()
        return res

    @api.model
    def fix_qty_received_inconsistencies(self, domain=None):
        base_domain = [
            ("product_id.type", "in", ["product", "consu"]),
            ("move_ids.state", "in", ["done"]),
            ("state", "!=", "cancel"),
        ]
        if domain:
            base_domain = ["&"] + base_domain + domain
        lines = self.search(base_domain)
        if not lines:
            return False
        lines._compute_qty_received_method()
        lines._compute_qty_received()
        return True


class PurchaseOrder(models.Model):
    _inherit = "purchase.order"

    def action_fix_qty_received_inconsistencies(self):
        lines = self.mapped("order_line")
        if lines:
            domain = [("id", "in", lines.ids)]
            self.env["purchase.order.line"].fix_qty_received_inconsistencies(domain=domain)
        return {"type": "ir.actions.act_window_close"}
