from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PurchaseCollection(models.Model):
    _name = 'purchase.collection'
    _description = 'Purchase Collection'
    _order = 'name'

    name = fields.Char(required=True)

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'El nombre de la colección debe ser único.'),
    ]

    def _check_purchase_collection_permission(self):
        if self.env.su:
            return
        if not self.env.user.allow_create_purchase_collection:
            raise UserError(_("No tienes permiso para gestionar colecciones de compra."))

    @api.model_create_multi
    def create(self, vals_list):
        self._check_purchase_collection_permission()
        return super().create(vals_list)

    def write(self, vals):
        self._check_purchase_collection_permission()
        return super().write(vals)

    def unlink(self):
        self._check_purchase_collection_permission()
        return super().unlink()
