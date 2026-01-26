from collections import defaultdict
from odoo import api, fields, models, _

class MrpProductionGroupComponentDetail(models.Model):
    _name = "mrp.production.group.component.detail"
    _description = "Componentes detallados por OF"
    _order = "production_id, id"

    group_id = fields.Many2one("mrp.production.group", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one(related="group_id.company_id", store=True, readonly=True)

    production_id = fields.Many2one("mrp.production", required=True, index=True, ondelete="cascade")
    move_id = fields.Many2one("stock.move", index=True)  # si viene de move_raw_ids, para navegar

    product_id = fields.Many2one("product.product", required=True, index=True)
    product_tmpl_id = fields.Many2one(related="product_id.product_tmpl_id", store=True, readonly=True)
    product_uom_id = fields.Many2one("uom.uom", required=True)
    qty = fields.Float(required=True)

    location_id = fields.Many2one("stock.location", index=True, string="Ubicación de Origen")  # ubicación origen prevista (la del picking type)
    
    excluded = fields.Boolean(string="Excluido", default=False, index=True)
    
    
    @api.model_create_multi
    def create(self, vals_list):
        recs = super().create(vals_list)
        if not self.env.context.get("skip_group_after_change"):
            groups = recs.mapped("group_id")
            if groups:
                groups._after_detail_change()
        return recs

    def write(self, vals):
        groups = self.mapped("group_id")
        res = super().write(vals)

        if self.env.context.get("skip_group_after_change"):
            return res

        relevant = {"excluded", "qty", "product_id", "product_uom_id", "location_id"}
        if relevant.intersection(vals.keys()):
            if groups:
                groups._after_detail_change()
        return res

    def unlink(self):
        groups = self.mapped("group_id")
        res = super().unlink()
        if not self.env.context.get("skip_group_after_change"):
            if groups:
                groups._after_detail_change()
        return res


class MrpProductionGroupComponent(models.Model):
    _name = "mrp.production.group.component"
    _description = "Componentes totalizados por grupo"
    _order = "product_id"

    group_id = fields.Many2one("mrp.production.group", required=True, index=True, ondelete="cascade")
    company_id = fields.Many2one(related="group_id.company_id", store=True, readonly=True)

    product_id = fields.Many2one("product.product", required=True, index=True)
    product_tmpl_id = fields.Many2one(related="product_id.product_tmpl_id", store=True, readonly=True)
    product_uom_id = fields.Many2one("uom.uom", required=True)
    qty_total = fields.Float(required=True)

    location_id = fields.Many2one("stock.location", index=True)

    qty_available_location_origin = fields.Float(compute="_compute_qty_available", readonly=True)
    

    @api.depends("product_id", "location_id", "company_id")
    def _compute_qty_available(self):
        for rec in self:
            p = rec.product_id
            if not p:
                rec.qty_available_location_origin = 0.0
                continue

            p = p.with_company(rec.company_id)

            if rec.location_id:
                rec.qty_available_location_origin = p.with_context(
                    location=rec.location_id.id,
                    compute_child=True,
                ).qty_available
            else:
                rec.qty_available_location_origin = 0.0
