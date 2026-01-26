# -*- coding: utf-8 -*-
from odoo import fields, models


class ResCompany(models.Model):
    _inherit = "res.company"

    account_advance_customer_id = fields.Many2one(
        comodel_name="account.account",
        string="Cuenta de anticipos de clientes",
        domain="[('deprecated', '=', False), ('internal_type', '=', 'other')]",
        help="Cuenta puente para anticipos de clientes (p.ej. 438).",
    )
