
#Intento de optimizacion de Yostesis.

from odoo import api, fields, models


class ProductProduct(models.Model):
    _inherit = "product.product"
    #campitos
    manual_code = fields.Boolean(
        string="Código manual",
        help="Marca si NO quieres que el sistema regenere default_code.",
        default=False,
        copy=False,
    )
    code_prefix_copy = fields.Char(copy=False)

    default_code = fields.Char(
        string="Internal Reference",
        compute="_compute_default_code",
        store=True,
        readonly=False,
        index=True,
        copy=False,
    )

    #compute pero """"optimizado""""    
    @api.depends('product_tmpl_id.code_prefix')
    def _compute_default_code(self):
        # pilla solo las variantes que realmente necesitan código
        to_update = self.filtered(
            lambda p: not p.manual_code and not p.code_prefix_copy
        )#es decir, que gracias a este filtro, me aseguro de que solo entran las variantes que no tienen manual_code y aun no tienen code_prefix_copy
        #si el codigo ya existe, entonces code_prefix_copy está lleno y la variante queda fuera del update
        if not to_update:
            return

        # las agrupa por plantilla
        tmpl_to_prods = {}
        for prod in to_update:
            tmpl_to_prods.setdefault(prod.product_tmpl_id, []).append(prod)

        # por plantilla saca todos los códigos de una tacada
        cr = self.env.cr
        for tmpl, prods in tmpl_to_prods.items():
            seq = tmpl.default_code_sequence_id
            if not seq:
                tmpl._create_default_code_sequence()
                seq = tmpl.default_code_sequence_id

            needed = len(prods)
            # nombre de verdad de la secuencia en prosgres
            db_seq_name = 'ir_sequence_%s' % seq.id

            #UNA sola query, mas tocha pero a la larga menos carga para el sistema
            cr.execute(
                "SELECT nextval(%s) FROM generate_series(1, %s)",
                (db_seq_name, needed),
            )
            codes = [row[0] for row in cr.fetchall()]

            # aseignación de los códigos
            for prod, code in zip(prods, codes):
                prod.default_code = str(code)
                prod.code_prefix_copy = str(code)
