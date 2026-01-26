# -*- coding: utf-8 -*-
from odoo import api, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    #write mas ligero pero evitando riesgos de revoltura de refInternas
    def write(self, vals):
        variant_change = 'attribute_line_ids' in vals

        if variant_change:
            # se desactiva la creación automática mientras se guarda 
            vals = vals.copy()
            vals['no_create_variants'] = 'yes'

        # guardado ligero
        res = super().write(vals)

        #si cambiarn atributos, se crean las variantes que faltan YA
        if variant_change:
            for tmpl in self:
                existing = set(tmpl.product_variant_ids.ids)

                tmpl.with_context(akua_force_generate=True).no_create_variants = 'no'
                tmpl.with_context(akua_force_generate=True)._create_variant_ids()

                new_ids = list(set(tmpl.product_variant_ids.ids) - existing)
                if not new_ids:
                    tmpl.no_create_variants = 'yes'
                    continue

                seq = tmpl.default_code_sequence_id or tmpl._create_default_code_sequence()
                needed = len(new_ids)
                cr = self.env.cr
                cr.execute(
                    "SELECT nextval(%s) FROM generate_series(1,%s)",
                    ('ir_sequence_%s' % seq.id, needed),
                )
                codes = [str(r[0]) for r in cr.fetchall()]

                for prod, code in zip(
                    tmpl.env['product.product'].browse(new_ids).filtered(lambda p: not p.manual_code),
                    codes,
                ):
                    prod.default_code = code
                    prod.code_prefix_copy = code

                tmpl.no_create_variants = 'yes'

        # si y solo sí, se cambia el prefijo, renumeramos como antes
        if 'code_prefix' in vals and not variant_change:
            seq = self.default_code_sequence_id
            if seq:
                for prod in self.product_variant_ids.filtered(lambda p: not p.manual_code):
                    prod.default_code = seq.next_by_id()
                    prod.code_prefix_copy = prod.default_code
        return res
