import re
import unicodedata
from odoo import api, fields, models

class MrpProductionGroupAttributeValueName(models.Model):
    _name = "mrp.production.group.attribute.value.name"
    _description = "Valor de atributo (nombre deduplicado por wizard)"

    wizard_key = fields.Char(index=True, required=True)
    name = fields.Char(required=True)
    name_key = fields.Char(index=True, required=False)
    def init(self):
        self._cr.execute("""
            UPDATE mrp_production_group_attribute_value_name
            SET name_key = lower(name)
            WHERE name_key IS NULL
            AND name IS NOT NULL
        """) #me petaba la BD


    _sql_constraints = [
        ("uniq_wizard_name_key", "unique(wizard_key, name_key)", "Valor duplicado para este wizard."),
    ]

    def _norm(self, s):
        s = s or ""
        s = unicodedata.normalize("NFKC", s)
        s = s.replace("\u00A0", " ")
        s = s.replace("\u200B", "")
        s = s.replace("\u2060", "")
        s = s.replace("×", "x")
        s = re.sub(r"\s+", " ", s).strip()
        return s

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            n = self._norm(vals.get("name"))
            vals["name"] = n
            vals["name_key"] = n.casefold()
        return super().create(vals_list)

    def write(self, vals):
        if "name" in vals:
            n = self._norm(vals.get("name"))
            vals["name"] = n
            vals["name_key"] = n.casefold()
        return super().write(vals)
