from odoo import fields, models


class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    production_group_id = fields.Many2one(
        comodel_name="mrp.production.group",
        string="AGOF",
        related="production_id.group_id",
        store=True,
        index=True,
        readonly=True,
    )
