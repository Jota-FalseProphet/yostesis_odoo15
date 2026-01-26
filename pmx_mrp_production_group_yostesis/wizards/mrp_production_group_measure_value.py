import re
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class MrpProductionGroupMeasureValue(models.TransientModel):
    _name = "mrp.production.group.measure.value"
    _description = "Wizard: valores de medida (tags)"
    _rec_name = "name"

    wizard_key = fields.Char(required=True, index=True)
    kind = fields.Selection(
        selection=[("length", "Largo"), ("height", "Alto"), ("width", "Ancho")],
        required=True,
        index=True,
    )
    name = fields.Char(required=True, index=True)
    value_float = fields.Float(required=True, index=True)
    value_key = fields.Char(required=True, index=True)

    _sql_constraints = [
        ("uniq_wiz_kind_key", "unique(wizard_key, kind, value_key)", "Valor duplicado."),
    ]

    def _parse_number(self, s):
        s = (s or "").strip()
        s = s.replace(",", ".")
        m = re.search(r"[-+]?\d+(\.\d+)?", s)
        if not m:
            raise UserError(_("Introduce solo un número (ej: 20, 29.5)."))
        return float(m.group(0))

    @api.model_create_multi
    def create(self, vals_list):
        out = []
        for vals in vals_list:
            v = vals.get("value_float")
            if v is None:
                v = self._parse_number(vals.get("name"))

            v = round(float(v), 2)
            canon = ("%s" % v).rstrip("0").rstrip(".")
            if not canon:
                canon = "0"

            vals["value_float"] = v
            vals["name"] = canon
            vals["value_key"] = canon.casefold()
            out.append(vals)
        return super().create(out)
