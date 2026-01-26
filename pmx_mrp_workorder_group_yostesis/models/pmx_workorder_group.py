from odoo import fields, models

class PmxWorkorderGroup(models.Model):
    _name = "pmx.workorder.group"
    _description = "Workorder Group"
    _order = "start_date desc, id desc"

    name = fields.Char(required=True, copy=False, default="New")
    start_date = fields.Datetime()
    state = fields.Selection(
        [("draft", "Draft"), ("in_progress", "In progress"), ("done", "Done")],
        default="draft",
        required=True,
    )
    workorder_ids = fields.One2many("mrp.workorder", "pmx_group_id")
