# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import fields, models, _
from odoo.exceptions import UserError

class MRPProductionToBatch(models.TransientModel):
    _name = 'mrp.production.to.group'
    _description = 'Group MRP Orders'

    group_id = fields.Many2one('mrp.production.group', string='Seleccionar agrupación')
    mode = fields.Selection([('existing', 'Un grupo de producción existente'), ('new', 'Un nuevo grupo de producción')], default='existing')

    def attach_orders(self):
        self.ensure_one()
        orders = self.env['mrp.production'].browse(self.env.context.get('active_ids'))
        if not orders:
            raise UserError(_("No hay órdenes seleccionadas."))
        ungrouped = orders.filtered(lambda m: not m.group_id)
        grouped = orders.filtered(lambda m: m.group_id)
        if grouped:
            grouped_reference = "".join(f"\n{order.name} → {order.group_name}" for order in grouped)
            raise UserError(_("Las siguientes órdenes ya están agrupadas:") + grouped_reference)
        if self.mode == 'new':
            company = ungrouped.company_id
            if len(company) > 1:
                raise UserError(_("Las órdenes seleccionadas pertenecen a más de una empresa."))
            group = self.env['mrp.production.group'].create({ 'company_id': company.id })
            group._set_start_date_if_empty()
        else:
            group = self.group_id

        ungrouped.write({'group_id': group.id})

        group.action_rebuild_components()

        return {
            "type": "ir.actions.act_window",
            "name": _("Agrupación de OF"),
            "res_model": "mrp.production.group",
            "view_mode": "form",
            "res_id": group.id,
            "target": "current",
        }
