from odoo import fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"

    manage_routes_from_variants = fields.Boolean(
        related='product_tmpl_id.manage_routes_from_variants',
        readonly=False,
    )

    def write(self, vals):
        # Cuando NO se gestionan rutas desde variantes y se edita una variante,
        # sincronizar de vuelta a la plantilla (y a las demás variantes)
        if 'route_ids' in vals and not self.env.context.get('template_route'):
            for product in self:
                tmpl = product.product_tmpl_id
                if not tmpl.manage_routes_from_variants and len(tmpl.product_variant_ids) > 1:
                    tmpl.with_context(product_route=True).write({
                        'route_ids': vals['route_ids'],
                    })
                    siblings = tmpl.product_variant_ids - product
                    if siblings:
                        siblings.with_context(template_route=True).write({
                            'route_ids': vals['route_ids'],
                        })
        return super().write(vals)
