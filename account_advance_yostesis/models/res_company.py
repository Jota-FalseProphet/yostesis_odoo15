# -*- coding: utf-8 -*-
from odoo import api, fields, models

class ResCompany(models.Model):
    _inherit = "res.company"

    account_advance_customer_id = fields.Many2one(
        "account.account",
        string="Cuenta de anticipos de clientes (438)",
        domain="[('company_id','=',id),('deprecated','=',False)]",
        help="Cuenta a la que se registrarán " \
        "los cobros por anticipos de clientes.")

    advance_transfer_journal_id = fields.Many2one(
        "account.journal",
        string="Diario para traspasos de anticipos",
        domain="[('company_id','=',id)]",
        help="Diario contable que se utilizará para los asientos de traspaso" \
        "438→430 al aplicar anticipos en facturas. Si se deja vacío, se usará " \
        "el primer diario general disponible.")

    account_advance_supplier_id = fields.Many2one(
            'account.account',
            string='Cuenta de anticipos a proveedores (407)',
            domain="[('company_id', '=', id), ('reconcile', '=', True), ('deprecated', '=', False)]",
            help="Ej. 407000000 Anticipos a proveedores (activo, conciliable)."
        )