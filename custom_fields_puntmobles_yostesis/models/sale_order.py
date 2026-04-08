import json
from lxml import etree
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    date_order = fields.Datetime(tracking=True)

    fecha_entrega_prevista = fields.Datetime(
        string='Fecha entrega prevista',
    )
    motivo_cambio_fecha_prevista = fields.Selection([
        ('peticion_cliente', 'Petición cliente'),
        ('solicitud_interna', 'Solicitud interna'),
    ], string='Motivo cambio fecha')

    is_commitment_readonly = fields.Boolean(
        compute='_compute_is_commitment_readonly',
    )

    @api.depends('state')
    def _compute_is_commitment_readonly(self):
        can_edit = self.env.user.allow_edit_commitment_confirmed
        for rec in self:
            rec.is_commitment_readonly = (
                rec.state in ('sale', 'done') and not can_edit
            )

    @api.onchange('commitment_date')
    def _onchange_commitment_date_to_prevista(self):
        for rec in self:
            if rec.commitment_date:
                rec.fecha_entrega_prevista = rec.commitment_date

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('fecha_entrega_prevista') and vals.get('commitment_date'):
                vals['fecha_entrega_prevista'] = vals['commitment_date']
        return super().create(vals_list)

    def write(self, vals):
        if 'commitment_date' in vals:
            if any(rec.state in ('sale', 'done') for rec in self):
                if not self.env.user.allow_edit_commitment_confirmed:
                    raise UserError(_(
                        'Solo los usuarios autorizados pueden modificar '
                        'la fecha de entrega en pedidos confirmados.'
                    ))

        if 'fecha_entrega_prevista' in vals:
            new_val = vals['fecha_entrega_prevista']
            motivo_key = vals.get('motivo_cambio_fecha_prevista')
            for rec in self:
                old_val = rec.fecha_entrega_prevista
                if not old_val and not new_val:
                    continue
                if rec.state in ('draft', 'sent'):
                    continue
                if not motivo_key:
                    motivo_key = rec.motivo_cambio_fecha_prevista
                if not motivo_key:
                    raise UserError(_(
                        'Debe indicar un motivo para cambiar la fecha de entrega prevista.'
                    ))
                motivo_label = dict(
                    self._fields['motivo_cambio_fecha_prevista'].selection
                ).get(motivo_key, motivo_key)
                old_str = fields.Datetime.to_string(old_val) if old_val else _('(vacío)')
                new_str = new_val or _('(vacío)')
                rec.message_post(
                    body=_(
                        '<strong>Fecha entrega prevista modificada</strong><br/>'
                        '%s → %s<br/>'
                        '<strong>Motivo:</strong> %s'
                    ) % (old_str, new_str, motivo_label),
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )
            vals['motivo_cambio_fecha_prevista'] = False

        elif 'motivo_cambio_fecha_prevista' in vals and vals['motivo_cambio_fecha_prevista']:
            motivo_key = vals['motivo_cambio_fecha_prevista']
            motivo_label = dict(
                self._fields['motivo_cambio_fecha_prevista'].selection
            ).get(motivo_key, motivo_key)
            for rec in self:
                rec.message_post(
                    body=_(
                        '<strong>Motivo cambio fecha actualizado</strong><br/>'
                        '<strong>Motivo:</strong> %s'
                    ) % motivo_label,
                    message_type='comment',
                    subtype_xmlid='mail.mt_note',
                )

        if 'commitment_date' in vals and 'fecha_entrega_prevista' not in vals:
            vals['fecha_entrega_prevista'] = vals['commitment_date']

        return super().write(vals)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super().fields_view_get(
            view_id=view_id, view_type=view_type,
            toolbar=toolbar, submenu=submenu,
        )
        if view_type != 'form':
            return res

        doc = etree.XML(res['arch'])

        for node in doc.xpath("//field[@name='expected_date']"):
            node.set('invisible', '1')
            modifiers = json.loads(node.get('modifiers') or '{}')
            modifiers['invisible'] = True
            node.set('modifiers', json.dumps(modifiers))

        already_injected = bool(doc.xpath("//field[@name='fecha_entrega_prevista']"))

        for node in doc.xpath("//field[@name='commitment_date']"):
            if self._is_in_subview(node):
                continue
            node.set('string', 'Fecha entrega establecida')

            modifiers = json.loads(node.get('modifiers') or '{}')
            readonly_cond = modifiers.get('readonly', [])
            new_cond = [('is_commitment_readonly', '=', True)]
            if readonly_cond:
                modifiers['readonly'] = ['|'] + new_cond + (
                    readonly_cond if isinstance(readonly_cond, list) else []
                )
            else:
                modifiers['readonly'] = new_cond
            node.set('modifiers', json.dumps(modifiers))
            node.set('attrs', json.dumps({'readonly': modifiers['readonly']}))

            if not already_injected:
                parent = node.getparent()
                idx = list(parent).index(node)
                readonly_el = etree.Element('field', {
                    'name': 'is_commitment_readonly',
                    'invisible': '1',
                    'modifiers': json.dumps({'invisible': True}),
                })
                prevista_el = etree.Element('field', {
                    'name': 'fecha_entrega_prevista',
                    'modifiers': '{}',
                })
                motivo_el = etree.Element('field', {
                    'name': 'motivo_cambio_fecha_prevista',
                    'modifiers': '{}',
                })
                parent.insert(idx + 1, readonly_el)
                parent.insert(idx + 2, prevista_el)
                parent.insert(idx + 3, motivo_el)
            break

        res['arch'] = etree.tostring(doc, encoding='unicode')

        extra_fields = (
            'fecha_entrega_prevista', 'motivo_cambio_fecha_prevista',
            'is_commitment_readonly',
        )
        for fname in extra_fields:
            if fname not in res.get('fields', {}):
                res['fields'].update(self.fields_get([fname]))

        return res

    @staticmethod
    def _is_in_subview(node):
        parent = node.getparent()
        while parent is not None:
            if parent.tag == 'field':
                return True
            parent = parent.getparent()
        return False
