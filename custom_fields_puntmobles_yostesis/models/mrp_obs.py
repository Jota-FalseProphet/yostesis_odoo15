from odoo import api, fields, models

class MrpProduction(models.Model):
    _inherit = "mrp.production"

    x_studio_obs_fabrica_del_producto = fields.Char(
        string="Obs FabrIca del Producto",
        compute="_compute_obs_fabrica",
        store=False,
    )

    @api.depends(
        "sale_line_id.x_studio_obs",
        "move_finished_ids.sale_line_id.x_studio_obs",
        "move_raw_ids.sale_line_id.x_studio_obs",
    )
    def _compute_obs_fabrica(self):
        for rec in self:
            val = False
            # 1) Camino directo si existe sale_line_id (sale_mrp)
            if hasattr(rec, "sale_line_id") and rec.sale_line_id:
                val = rec.sale_line_id.x_studio_obs
            # 2) Fallback por movimientos (por si acaso)
            if not val:
                moves = rec.move_finished_ids.filtered(lambda m: m.sale_line_id) or rec.move_raw_ids.filtered(lambda m: m.sale_line_id)
                sol = moves[:1].sale_line_id
                val = sol.x_studio_obs if sol else False
            rec.x_studio_obs_fabrica_del_producto = val
