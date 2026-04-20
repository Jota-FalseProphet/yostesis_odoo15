from markupsafe import Markup

from odoo import _, api, fields, models


class PurchaseOrderLine(models.Model):
    _inherit = 'purchase.order.line'

    date_planned_vendory = fields.Datetime(
        string="Fecha propuesta por proveedor",
        help="Fecha que el proveedor propone desde el portal. "
             "No modifica la fecha real (date_planned) del pedido: "
             "queda aqui para que el comprador decida si la aplica.",
    )


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    has_vendor_proposed_datesy = fields.Boolean(
        string="Hay fechas propuestas por proveedor",
        compute='_compute_has_vendor_proposed_datesy',
    )

    @api.depends('order_line.date_planned_vendory', 'order_line.date_planned')
    def _compute_has_vendor_proposed_datesy(self):
        for order in self:
            order.has_vendor_proposed_datesy = any(
                line.date_planned_vendory
                and line.date_planned_vendory != line.date_planned
                for line in order.order_line
            )

    def _update_date_planned_for_lines(self, updated_dates):
        """Override: el proveedor NO sobreescribe date_planned.
        La fecha propuesta se guarda en date_planned_vendory por linea
        y se registra en el chatter + actividad para el comprador.
        """
        self.ensure_one()
        for line, new_date in updated_dates:
            line.date_planned_vendory = new_date

        body = Markup('<p>%s</p>') % _(
            "%s ha propuesto nuevas fechas de entrega desde el portal "
            "(pendientes de revision por el comprador):",
            self.partner_id.display_name,
        )
        body += Markup('<ul>')
        for line, new_date in updated_dates:
            current = line.date_planned.date() if line.date_planned else '-'
            body += Markup('<li>%s: %s &rarr; <strong>%s</strong></li>') % (
                line.product_id.display_name,
                current,
                new_date.date(),
            )
        body += Markup('</ul>')
        self.message_post(body=body)

        activity = self.env['mail.activity'].search([
            ('summary', '=', _("Fecha propuesta por proveedor")),
            ('res_model_id', '=', self.env.ref('purchase.model_purchase_order').id),
            ('res_id', '=', self.id),
            ('user_id', '=', self.user_id.id),
        ], limit=1)
        if activity:
            activity.note = (activity.note or '') + body
        else:
            activity = self.activity_schedule(
                'mail.mail_activity_data_warning',
                summary=_("Fecha propuesta por proveedor"),
                user_id=self.user_id.id or self.env.user.id,
            )
            activity.note = body

    def action_apply_vendor_proposed_datesy(self):
        """Copia date_planned_vendory a date_planned en cada linea que
        tenga una propuesta pendiente. Deja el campo propuesta a False
        y registra el cambio en el chatter."""
        for order in self:
            applied = []
            for line in order.order_line:
                if (
                    line.date_planned_vendory
                    and line.date_planned_vendory != line.date_planned
                ):
                    old_date = line.date_planned.date() if line.date_planned else '-'
                    new_date = line.date_planned_vendory.date()
                    line.date_planned = line.date_planned_vendory
                    line.date_planned_vendory = False
                    applied.append((line.product_id.display_name, old_date, new_date))

            if applied:
                body = Markup('<p>%s</p>') % _(
                    "Se han aplicado las fechas propuestas por el proveedor:"
                )
                body += Markup('<ul>')
                for product_name, old_date, new_date in applied:
                    body += Markup('<li>%s: %s &rarr; <strong>%s</strong></li>') % (
                        product_name, old_date, new_date,
                    )
                body += Markup('</ul>')
                order.message_post(body=body)
        return True
