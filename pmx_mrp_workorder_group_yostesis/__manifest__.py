{
    "name": "PMX Workorder Grouping",
    "version": "15.0.1.3.3",
    "category": "Manufacturing",
    "depends": ["mrp"],
    "summary": "Agrupa y gestiona órdenes de trabajo en lotes con operaciones batch",
    "description": """
        Permite agrupar y gestionar de forma eficiente múltiples órdenes de trabajo 
        (workorders) en la manufactura de Odoo.
        
        Comportamiento principal:
        - Crea un modelo "pmx.workorder.group" para agrupar órdenes relacionadas.
        - Proporciona operaciones en lote: iniciar, pausar, finalizar múltiples órdenes.
        - Permite reapertura individual de órdenes finalizadas erróneamente.
        - Añade campos de vinculación y visibilidad del grupo en órdenes de trabajo.
        - Menú PMX en Manufactura para gestionar grupos de trabajo.
        
        Usos:
        - Organizar la producción por lotes, turnos o proyectos.
        - Acelerar operaciones repetitivas sobre múltiples órdenes simultáneamente.
        - Rastrear y gestionar grupos de trabajo relacionados.
        - Recuperar órdenes finalizadas erróneamente con reapertura controlada.
    """,
    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        # "data/ir_cron.xml",
        "views/pmx_workorder_group_views.xml",
        # "views/stock_picking_type_views.xml",
        "views/mrp_workorder_views.xml",
        "views/server_actions.xml",
    ],
    "application": False,
    "installable": True,
}
