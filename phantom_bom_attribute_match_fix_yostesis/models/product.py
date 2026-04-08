from odoo import models
from odoo.addons.stock.models.product import Product as StockProduct


class ProductProduct(models.Model):
    _inherit = "product.product"

    def _compute_quantities_dict(
        self, lot_id, owner_id, package_id, from_date=False, to_date=False
    ):
        bom_kits = self.env["mrp.bom"]._bom_find(self, bom_type="phantom")
        kits = self.filtered(lambda p: bom_kits.get(p))
        if not kits:
            return super()._compute_quantities_dict(
                lot_id, owner_id, package_id,
                from_date=from_date, to_date=to_date,
            )

        non_kits = self - kits
        res = {}
        if non_kits:
            res.update(
                super(ProductProduct, non_kits)._compute_quantities_dict(
                    lot_id, owner_id, package_id,
                    from_date=from_date, to_date=to_date,
                )
            )

        if kits:
            res.update(
                StockProduct._compute_quantities_dict(
                    kits, lot_id, owner_id, package_id,
                    from_date=from_date, to_date=to_date,
                )
            )

        return res
