# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError

class ProductTemplate(models.Model):
    _inherit = "product.template"

    def _sanitize_prefix(self, cp):
        """Normaliza el prefijo: quita espacios, deja A-Z0-9_- y limita longitud."""
        if cp is None:
            return None
        if isinstance(cp, bool):
            return None if cp is False else str(cp)
        s = str(cp).strip()
        if not s:
            return None
        s = re.sub(r'\s+', '', s).upper()
        s = re.sub(r'[^A-Z0-9_-]', '', s)
        return s[:20] or None

    def write(self, vals):
        if 'code_prefix' in vals:
            cp = self._sanitize_prefix(vals.get('code_prefix'))
            if not cp:
                raise ValidationError(_("Code Prefix cannot be empty."))
            vals = dict(vals)
            vals['code_prefix'] = cp

        manual_snapshot = {}
        auto_ids_by_tmpl = {}

        if 'code_prefix' in vals:
            for tmpl in self:
                manuals = tmpl.product_variant_ids.filtered(lambda r: getattr(r, "manual_code", False))
                autos = tmpl.product_variant_ids.filtered(lambda r: not getattr(r, "manual_code", False))
                manual_snapshot[tmpl.id] = manuals.read(['id', 'default_code', 'code_prefix_copy'])
                auto_ids_by_tmpl[tmpl.id] = autos.ids

        res = super(ProductTemplate, self).write(vals)

        if 'code_prefix' in vals:
            for tmpl in self:
                for row in manual_snapshot.get(tmpl.id, []):
                    p = self.env['product.product'].browse(row['id'])
                    p.with_context(auto_default_code=True).write({
                        'default_code': row['default_code'],
                        'code_prefix_copy': row['code_prefix_copy'],
                    })

            for tmpl in self:
                auto_ids = auto_ids_by_tmpl.get(tmpl.id, [])
                if auto_ids:
                    self.env['product.product'].browse(auto_ids).write({'manual_code': False})

            for tmpl in self:
                autos_bad = tmpl.product_variant_ids.filtered(
                    lambda p: not getattr(p, 'manual_code', False)
                    and isinstance(p.default_code, str)
                    and p.default_code.strip().lower() == 'false'
                )
                if autos_bad:
                    autos_bad.with_context(auto_default_code=True).write({
                        'default_code': False,
                        'code_prefix_copy': False,
                    })
                    for p in autos_bad:
                        p.with_context(auto_default_code=True)._default_code_compute()

        return res
