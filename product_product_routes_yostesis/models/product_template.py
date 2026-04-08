from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    manage_routes_from_variants = fields.Boolean(
        string="Gestionar rutas desde las variantes",
        default=False,
    )

    def write(self, vals):
        # Al desmarcar el check, propagar rutas de plantilla a todas las variantes
        if 'manage_routes_from_variants' in vals and not vals['manage_routes_from_variants']:
            for template in self:
                if template.manage_routes_from_variants and template.route_ids:
                    template.product_variant_ids.with_context(template_route=True).write({
                        'route_ids': [(6, 0, template.route_ids.ids)],
                    })

        res = super().write(vals)

        # Cuando NO se gestionan desde variantes y se cambian rutas, propagar a variantes
        if 'route_ids' in vals and not self.env.context.get('product_route'):
            for template in self:
                if not template.manage_routes_from_variants:
                    template.product_variant_ids.with_context(template_route=True).write({
                        'route_ids': [(6, 0, template.route_ids.ids)],
                    })

        return res
