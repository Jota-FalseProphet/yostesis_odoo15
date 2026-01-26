import logging
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    pmx_mrp_group_target_picking_type_id = fields.Many2one(
        "stock.picking.type",
        string="Tipo operación para la Agrupación OFs",
        help=(
            "Cuando el wizard de Agrupación de Órdenes de Fabricación filtra por este Tipo de Operación "
            "(normalmente de Fabricación), la agrupación guardará como 'Tipo de operación' el valor configurado aquí."
        ),
    )

    def pmx_get_mrp_group_target_picking_type(self, strict=True):
        """Devuelve STP3 a partir de STP1 (self)."""
        self.ensure_one()
        stp1 = self
        stp3 = stp1
        if stp1.code == "mrp_operation":
            stp3 = stp1.pmx_mrp_group_target_picking_type_id
            if strict and not stp3:
                raise UserError(_(
                    "El Tipo de operación '%s' no tiene configurado 'Tipo operación para Agrupación OFs' (STP3)."
                ) % stp1.display_name)
        return stp3
