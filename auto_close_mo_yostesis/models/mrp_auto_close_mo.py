from odoo.exceptions import ValidationError
import logging
from odoo import api, fields, models, _

_logger = logging.getLogger(__name__)

class StockPickingType(models.Model):
    _inherit = "stock.picking.type"

    pmx_auto_close_mo = fields.Boolean(string="Auto Cerrar OFs")
    pmx_auto_close_mo_from = fields.Datetime(string="Auto cerrar OF desde")

    @api.constrains("pmx_auto_close_mo", "pmx_auto_close_mo_from", "code")
    def _check_pmx_auto_close_from(self):
        for pt in self:
            if pt.pmx_auto_close_mo and pt.code == "mrp_operation" and not pt.pmx_auto_close_mo_from:
                raise ValidationError(_("Debes indicar 'Auto cerrar OF desde' cuando activas el autocierre."))


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    @api.model
    def pmx_cron_auto_close_to_close(self, limit=200):
        scan_limit = limit * 10

        mos = self.sudo().search(
            [
                ("state", "=", "to_close"),
                ("picking_type_id.pmx_auto_close_mo", "=", True),
                ("picking_type_id.pmx_auto_close_mo_from", "!=", False),
            ],
            order="id asc",
            limit=scan_limit,
        )

        ctx = dict(
            self.env.context,
            pmx_auto_close_cron=True,
            mail_notrack=True,
            tracking_disable=True,
            mail_auto_subscribe_no_notify=True,
            mail_notify_force_send=False,
        )

        closed = 0
        for mo in mos:
            if closed >= limit:
                break

            with self.env.cr.savepoint():
                pt = mo.picking_type_id
                from_dt = pt.pmx_auto_close_mo_from
                if not from_dt:
                    continue

                anchor_dt = mo.date_planned_start or mo.create_date
                if anchor_dt and anchor_dt < from_dt:
                    continue

                wos = mo.workorder_ids
                if not wos or any(wo.state not in ("done", "cancel") for wo in wos):
                    continue

                res = mo.with_context(ctx).sudo().button_mark_done()
                mo.invalidate_cache()

                if mo.state == "done":
                    closed += 1
                    _logger.info("PMX auto-closed MO id=%s name=%s", mo.id, mo.name)
                else:
                    if isinstance(res, dict) and res.get("res_model"):
                        _logger.info(
                            "PMX auto-close blocked MO id=%s name=%s by %s",
                            mo.id, mo.name, res.get("res_model"),
                        )
                    else:
                        _logger.info(
                            "PMX auto-close did not finish MO id=%s name=%s state=%s",
                            mo.id, mo.name, mo.state,
                        )

        _logger.info("PMX auto-close summary scanned=%s closed=%s", len(mos), closed)
        return True
