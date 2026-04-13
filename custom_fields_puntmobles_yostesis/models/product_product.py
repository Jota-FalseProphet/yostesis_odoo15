from odoo import models, fields, api, _

class ProductProduct(models.Model):
    _inherit = 'product.product'
    
    # Añadido tracking al campo default_code (Referencia interna)
    # copy=False: al duplicar un producto no se arrastra la referencia interna
    default_code = fields.Char(tracking=True, copy=False)


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # copy=False: al duplicar la plantilla no se arrastran prefijo ni referencia
    code_prefix = fields.Char(copy=False)
    default_code = fields.Char(copy=False)

    # No se puede confirmar si el Subtotal es = 0
    @api.onchange('code_prefix')
    def _onchange_code_prefix_unique(self):
        if not self.code_prefix:
            return
        domain = [('code_prefix', '=', self.code_prefix)]
        if self.id.origin:
            domain.append(('id', '!=', self.id.origin))
        if self.env['product.template'].search(domain, limit=1):
            return {'warning': {
                'title': _("Nota:"),
                'message': _("El prefijo de referencia '%s' ya existe.", self.code_prefix),
            }}