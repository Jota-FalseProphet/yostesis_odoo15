from odoo import fields, models, _
from odoo.exceptions import UserError

class MrpWorkorder(models.Model):
    _inherit = "mrp.workorder"

    pmx_group_id = fields.Many2one("pmx.workorder.group", index=True)
    pmx_group_name = fields.Char(related="pmx_group_id.name", store=True, readonly=True, index=True)
    pmx_group_start_date = fields.Datetime(related="pmx_group_id.start_date", store=True, readonly=True, index=True)


    def pmx_action_start_batch(self):
        failed = []
        for wo in self:
            try:
                if wo.state in ("done", "cancel"):
                    continue

                open_time = wo.time_ids.filtered(lambda t: not t.date_end)
                if open_time:
                    continue

                wo.button_start()
            except Exception as e:
                failed.append("%s: %s" % (wo.display_name, str(e)))
        if failed:
            raise UserError(_("Some workorders could not be started:\n%s") % "\n".join(failed))
        return True


    def pmx_action_pause_batch(self):
        failed = []
        for wo in self:
            try:
                if wo.state != "progress":
                    continue
                wo.button_pending()
            except Exception as e:
                failed.append("%s: %s" % (wo.display_name, str(e)))
        if failed:
            raise UserError(_("Some workorders could not be paused:\n%s") % "\n".join(failed))
        return True


    def pmx_action_finish_batch(self):
        failed = []
        for wo in self:
            try:
                if wo.state not in ("progress", "ready"):
                    continue
                wo.button_finish()
            except Exception as e:
                failed.append("%s: %s" % (wo.display_name, str(e)))
        if failed:
            raise UserError(_("Some workorders could not be finished:\n%s") % "\n".join(failed))
        return True

    def pmx_action_reopen_done_single(self):
        if len(self) != 1:
            raise UserError(_("Selecciona una sola Orden de trabajo para reabrir."))

        self = self[0]

        if self.state != "done":
            raise UserError(_("Solo puedes reabrir una Orden de trabajo en estado Hecho (done)."))

        mo = self.production_id
        if not mo:
            raise UserError(_("La Orden de trabajo no tiene Orden de fabricación asociada."))

        if mo.state in ("done", "cancel"):
            raise UserError(_(
                "No se puede reabrir la Orden de trabajo porque su Orden de fabricación está en estado '%s'."
            ) % mo.state)

        if mo.state == "to_close":
            mo_vals = {"state": "progress"}
            if "date_finished" in mo._fields:
                mo_vals["date_finished"] = False
            if "is_locked" in mo._fields:
                mo_vals["is_locked"] = False
            mo.write(mo_vals)

        now = fields.Datetime.now()

        open_prod = self.env["mrp.workcenter.productivity"].sudo().search([
            ("workorder_id", "=", self.id),
            ("date_end", "=", False),
        ])
        if open_prod:
            open_prod.write({"date_end": now})

        wo_vals = {
            "state": "progress",
            "date_finished": False,
        }
        if not self.date_start:
            wo_vals["date_start"] = now

        self.write(wo_vals)
        return True