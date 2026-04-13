# Copyright 2024 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

from odoo import api, fields, models


class Product(models.Model):
    _inherit = "product.product"

    route_ids = fields.Many2many(
        "stock.location.route",
        "product_routes_rel",
        "product_id",
        "route_id",
        string="Routes",
        domain=[("product_selectable", "=", True)],
    )

    @api.model
    def create(self, vals):
        if "product_tmpl_id" in vals:
            if self._context.get("routes", False):
                vals["route_ids"] = self._context.get("routes", False)
            else:
                template = self.env["product.template"].browse(vals["product_tmpl_id"])
                if template.route_ids:
                    vals["route_ids"] = [(6, 0, template.route_ids.ids)]
        return super().create(vals)

    def write(self, vals):
        for product in self:
            if 'route_ids' in vals and len(product.product_tmpl_id.product_variant_ids.ids) == 1 and not self.env.context.get('template_route'):
                product.product_tmpl_id.with_context(product_route=True).write({
                    'route_ids': vals['route_ids'],
                })
        return super().write(vals)


class ProductTemplate(models.Model):
    _inherit = "product.template"

    @api.model
    def create(self, vals):
        res = super(
            ProductTemplate, self.with_context(routes=vals.get("route_ids", False))
        ).create(vals)
        return res

    def write(self, vals):
        for template in self:
            if 'route_ids' in vals and len(template.product_variant_ids.ids) == 1 and not self.env.context.get('product_route'):
                template.product_variant_ids.with_context(template_route=True).write({
                    'route_ids': vals['route_ids'],
                })
        return super().write(vals)
