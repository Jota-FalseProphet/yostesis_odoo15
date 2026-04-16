from odoo import fields, models


class ProjectTask(models.Model):
    _inherit = 'project.task'

    is_asistecs_project = fields.Boolean(
        related='project_id.is_asistecs_project',
        store=False,
    )
    asistecs_documentation = fields.Text(
        string="Documentacion",
        help="Notas de desarrollo: resoluciones, decisiones tecnicas, "
             "pasos seguidos para cada incidencia o desarrollo.",
    )
