# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ProductProduct(models.Model):
    _inherit = "product.product"
    # Parchea product_product.py de indaws_internal_reference

    # Re-declaramos el campo para añadir inverse y evitar write() en compute
    default_code = fields.Char(
        compute="_default_code_compute",     # reutilizamos el nombre para que lo coja este compute
        inverse="_inverse_default_code",     # ahora editable en UI/Shell
        store=True,
        index=True,
        readonly=False,
        copy=False,
    )

    # IMPORTANTE: no redefinimos manual_code; ya existe en la BD.
    # También dejamos el code_prefix_copy que usa el módulo de indaws.

    def write(self, vals):
        # 🔒 Normaliza "False" (string) => False real, venga de donde venga
        if 'default_code' in vals and isinstance(vals['default_code'], str) and vals['default_code'].strip().lower() == 'false':
            vals = dict(vals)
            vals['default_code'] = False

        # Si el usuario quiere volver a AUTO (manual_code=False) y limpia default_code,
        # limpiamos también code_prefix_copy para que el write() del módulo original
        # NO recoloque el código anterior.
        if vals.get('manual_code') is False and ('default_code' in vals and not vals['default_code']):
            vals = dict(vals)  # copiar por seguridad
            vals.setdefault('code_prefix_copy', False)

        return super().write(vals)

    # Versión segura del generador para evitar "False" como texto
    def _generate_default_code(self):
        self.ensure_one()
        code = False
        if self.product_tmpl_id.code_prefix:
            if not getattr(self.product_tmpl_id, 'default_code_sequence_id', False):
                self.product_tmpl_id._create_default_code_sequence()
            if self.default_code:
                code = self.default_code
            else:
                seq_code = "product_tmpl_id_%s_code_reference" % self.product_tmpl_id.id
                seq = self.env['ir.sequence'].next_by_code(seq_code)
                code = seq or False  
        if isinstance(code, str) and code.strip().lower() == 'false':
            code = False
        return code

    @api.depends("product_tmpl_id.code_prefix")
    def _default_code_compute(self):
        """Respeta manuales. Si no es manual: genera por secuencia del template.
        Sin write() dentro del compute (asignación directa)."""
        for rec in self:
            if getattr(rec, "manual_code", False):
                continue
            raw = rec._generate_default_code()
            if isinstance(raw, str) and raw.strip().lower() == 'false':
                raw = False
            rec.default_code = raw or False
            rec.code_prefix_copy = rec.default_code

    def _inverse_default_code(self):
        """Si el usuario escribe un código, marcamos modo manual y sincronizamos la copia.
        Si el contexto indica que es automático (al cambiar prefijo), no activamos manual."""
        auto = self.env.context.get("auto_default_code")
        for rec in self:
            if not auto:
                if hasattr(rec, "manual_code"):
                    rec.manual_code = bool(rec.default_code)
            rec.code_prefix_copy = rec.default_code

    def action_reset_default_code_to_auto(self):
        """Volver a modo AUTO: limpiar y recomputar en contexto 'auto'."""
        for rec in self:
            rec.with_context(auto_default_code=True).write({
                'manual_code': False,
                'default_code': False,
                'code_prefix_copy': False,
            })
            rec.with_context(auto_default_code=True)._default_code_compute()
            rec.invalidate_cache(['default_code', 'manual_code', 'code_prefix_copy'])
