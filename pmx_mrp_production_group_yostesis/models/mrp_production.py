from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    group_id = fields.Many2one(
        "mrp.production.group",
        index=True,
        copy=False
    )
    group_name = fields.Char(related="group_id.name", store=True)
    group_start_date = fields.Date(
        related="group_id.start_date",
        string="Fecha de agrupación",
        store=True
    )
    # group_origin_display = fields.Char(compute="_compute_group_origin_display")
    product_id_display = fields.Many2one(
        "product.product",
        related="product_id",
        readonly=True,
        string="Producto",
    )
    product_qty_display = fields.Float(related="product_qty", readonly=True, string="Cantidad")
    production_link_id = fields.Many2one(
        comodel_name="mrp.production",
        string="OF",
        compute="_compute_production_link_id",
        store=False
    )
    sale_order_origin_id = fields.Many2one(
        comodel_name="sale.order",
        string="Pedido de venta",
        compute="_compute_sale_order_origin_id",
        readonly=True
    )
    sale_order_id = fields.Many2one(
        "sale.order",
        string="Pedido de venta",
        compute="_compute_sale_links",
        readonly=True
    )
    sale_product_id = fields.Many2one(
        "product.product",
        string="Producto de venta",
        compute="_compute_sale_links",
        readonly=True
    )

    @api.depends("procurement_group_id", "origin")
    def _compute_sale_links(self):
        SaleOrder = self.env["sale.order"]
        has_sale_line_field = "sale_line_id" in self._fields
        has_move_dest = "move_dest_ids" in self._fields
        stock_move_has_sol = "sale_line_id" in self.env["stock.move"]._fields

        groups = self.mapped("procurement_group_id")
        so_by_group = {}
        if groups:
            for so in SaleOrder.search([("procurement_group_id", "in", groups.ids)]):
                so_by_group.setdefault(so.procurement_group_id.id, so)

        for mo in self:
            so = False
            sol = False

            if has_sale_line_field:
                sol = mo.sale_line_id
            if not sol and has_move_dest and stock_move_has_sol:
                sol = (mo.move_dest_ids.mapped("sale_line_id")).filtered(lambda l: l)[:1]
            if sol:
                so = sol.order_id
            if not so and mo.procurement_group_id:
                so = so_by_group.get(mo.procurement_group_id.id)
            if not so and mo.origin:
                so = SaleOrder.search([("name", "=", mo.origin)], limit=1)

            mo.sale_order_id = so.id if so else False
            mo.sale_product_id = sol.product_id.id if sol else False

    def _compute_production_link_id(self):
        for rec in self:
            rec.production_link_id = rec

    def _compute_sale_order_origin_id(self):
        if "sale_line_id" not in self._fields:
            for mo in self:
                mo.sale_order_origin_id = False
            return

        for mo in self:
            mo.sale_order_origin_id = mo.sale_line_id.order_id if mo.sale_line_id else False

    def action_open_production_form(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "mrp.production",
            "view_mode": "form",
            "res_id": self.id,
            "target": "current",
        }

    def action_remove_from_group(self):
        for rec in self:
            rec.group_id = False
        return True

    @api.model
    def action_open_filter_wizard(self, active_ids=None):
        active_ids = active_ids or []

        ctx = dict(self.env.context or {})
        ctx.update({
            "active_model": "mrp.production",
            "active_ids": active_ids,
            "active_id": active_ids[0] if len(active_ids) == 1 else False,
        })

        return {
            "type": "ir.actions.act_window",
            "name": _("Filtro avanzado"),
            "res_model": "mrp.production.group.add.wizard",
            "view_mode": "form",
            "views": [(False, "form")],
            "target": "new",
            "context": ctx,
        }

    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        groups = recs.mapped("group_id")
        for g in groups:
            g._ensure_details_for_mos(recs.filtered(lambda r: r.group_id == g))
        return recs

    def write(self, vals):
        old_group_map = {mo.id: mo.group_id for mo in self}
        res = super().write(vals)

        if "group_id" not in vals:
            return res

        added = defaultdict(lambda: self.env["mrp.production"])
        removed = defaultdict(lambda: self.env["mrp.production"])

        for mo in self:
            old_group = old_group_map.get(mo.id)
            new_group = mo.group_id

            if old_group and old_group != new_group:
                removed[old_group.id] |= mo

            if new_group and old_group != new_group:
                added[new_group.id] |= mo

        Group = self.env["mrp.production.group"].sudo()

        for gid, mos in removed.items():
            group = Group.browse(gid).exists()
            if group:
                group._remove_details_for_mos(mos)

        for gid, mos in added.items():
            group = Group.browse(gid).exists()
            if group:
                group._ensure_details_for_mos(mos)

        return res