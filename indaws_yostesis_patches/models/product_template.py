# -*- coding: utf-8 -*-
import re
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ProductTemplate(models.Model):
    _inherit = "product.template"

    default_code_sequence_id = fields.Many2one(
        comodel_name="ir.sequence",
        string="Default code internal reference",
        copy=False,
    )

    def _sanitize_prefix(self, cp):
        if cp is None:
            return None
        if isinstance(cp, bool):
            return None if cp is False else str(cp)
        s = str(cp).strip()
        if not s:
            return None
        s = re.sub(r"\s+", "", s).upper()
        s = re.sub(r"[^A-Z0-9_-]", "", s)
        return s[:20] or None

    def _seq_code_for_tmpl(self, tmpl):
        return f"product_tmpl_id_{tmpl.id}_code_reference"

    def _pick_and_dedupe_sequence(self, tmpl):
        SEQ = self.env["ir.sequence"].sudo()
        seq_code = self._seq_code_for_tmpl(tmpl)
        company_id = tmpl.company_id.id if tmpl.company_id else False

        seqs = SEQ.search([("code", "=", seq_code)])
        if not seqs:
            seq = SEQ.create(
                {
                    "name": f"{tmpl.name}_Internal Reference",
                    "prefix": f"{tmpl.code_prefix}-",
                    "code": seq_code,
                    "implementation": "standard",
                    "padding": 5,
                    "number_increment": 1,
                    "company_id": company_id,
                }
            )
            if seq.number_next_actual < 1:
                seq.number_next_actual = 1
            return seq

        exact = seqs.filtered(lambda s: (s.company_id.id if s.company_id else False) == company_id)
        chosen = (exact or seqs)[:1]

        dupes = seqs - chosen
        if dupes:
            dupes.write({"active": False})

        if company_id and not chosen.company_id:
            chosen.company_id = company_id

        if chosen.prefix != f"{tmpl.code_prefix}-":
            chosen.prefix = f"{tmpl.code_prefix}-"

        if chosen.number_next_actual < 1:
            chosen.number_next_actual = 1

        reset_next = self.env.context.get("reset_default_code_sequence", True)
        if reset_next:
            chosen.number_next_actual = 1

        return chosen

    def _ensure_default_code_sequence(self):
        for tmpl in self:
            if not tmpl.code_prefix:
                continue

            seq = tmpl._pick_and_dedupe_sequence(tmpl)

            if tmpl.default_code_sequence_id.id != seq.id:
                tmpl.with_context(skip_internal_reference_post=True).write(
                    {"default_code_sequence_id": seq.id}
                )

    def write(self, vals):
        if self.env.context.get("skip_internal_reference_post"):
            return super().write(vals)

        if "code_prefix" in vals:
            cp = self._sanitize_prefix(vals.get("code_prefix"))
            if not cp:
                raise ValidationError(_("Code Prefix cannot be empty."))
            vals = dict(vals)
            vals["code_prefix"] = cp

        manual_snapshot = {}
        auto_ids_by_tmpl = {}

        if "code_prefix" in vals:
            for tmpl in self:
                manuals = tmpl.product_variant_ids.filtered(
                    lambda r: getattr(r, "manual_code", False)
                )
                autos = tmpl.product_variant_ids.filtered(
                    lambda r: not getattr(r, "manual_code", False)
                )
                manual_snapshot[tmpl.id] = manuals.read(
                    ["id", "default_code", "code_prefix_copy"]
                )
                auto_ids_by_tmpl[tmpl.id] = autos.ids

        res = super().write(vals)

        if "code_prefix" in vals:
            self._ensure_default_code_sequence()

            for tmpl in self:
                auto_ids = auto_ids_by_tmpl.get(tmpl.id, [])
                if not auto_ids:
                    continue

                seq_code = self._seq_code_for_tmpl(tmpl)
                prods = self.env["product.product"].browse(auto_ids)

                prods.with_context(auto_default_code=True).write({"manual_code": False})

                for p in prods:
                    nxt = self.env["ir.sequence"].next_by_code(seq_code)
                    p.with_context(auto_default_code=True).write(
                        {
                            "default_code": nxt or False,
                            "code_prefix_copy": nxt or False,
                        }
                    )

            for tmpl in self:
                for row in manual_snapshot.get(tmpl.id, []):
                    p = self.env["product.product"].browse(row["id"])
                    p.with_context(auto_default_code=True).write(
                        {
                            "default_code": row["default_code"],
                            "code_prefix_copy": row["code_prefix_copy"],
                        }
                    )

            for tmpl in self:
                autos_bad = tmpl.product_variant_ids.filtered(
                    lambda p: not getattr(p, "manual_code", False)
                    and isinstance(p.default_code, str)
                    and p.default_code.strip().lower() == "false"
                )
                if autos_bad:
                    autos_bad.with_context(auto_default_code=True).write(
                        {"default_code": False, "code_prefix_copy": False}
                    )
                    for p in autos_bad:
                        p.with_context(auto_default_code=True)._default_code_compute()

        return res
