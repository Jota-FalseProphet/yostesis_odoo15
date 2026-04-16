from odoo import fields, models


class ProjectProject(models.Model):
    _inherit = 'project.project'

    is_asistecs_project = fields.Boolean(
        string="Proyecto de Asistecs",
        help="Si se activa, las tareas de este proyecto mostraran "
             "una pestana 'Documentacion' para que los devs "
             "registren resoluciones de incidencias y desarrollos.",
    )
