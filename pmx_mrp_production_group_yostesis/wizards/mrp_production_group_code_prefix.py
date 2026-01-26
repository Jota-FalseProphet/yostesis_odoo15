from odoo import models, fields

class MrpProductionGroupCodePrefix(models.Model):
    _name = "mrp.production.group.code_prefix"
    _description = "Prefijo de código (code_prefix)"
    _order = "name"

    name = fields.Char(required=True, index=True)
    company_id = fields.Many2one(
        "res.company",
        required=True,
        index=True,
        default=lambda self: self.env.company,
    )

    _sql_constraints = [
        ("uniq_company_name", "unique(company_id, name)", "El prefijo ya existe para esta compañía."),
    ]
