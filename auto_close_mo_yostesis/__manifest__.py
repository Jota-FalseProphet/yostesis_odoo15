{
    "name": "Auto Cerrar Órdenes de Fabricación",
    "version": "15.0.1.1.0",
    "category": "Manufacturing",
    "depends": ["mrp", "stock"],
    "summary": "Cierre automático de órdenes de fabricación cuando todas las operaciones están completas",
    "description": """
        Automatiza el cierre de órdenes de fabricación en estado "Para Cerrar" cuando todas 
        sus operaciones de taller están finalizadas (done o cancel).
        
        Comportamiento principal:
        - Añade opciones de autocierre en la configuración de tipos de operación.
        - Proporciona un cron (scheduled action) que se ejecuta cada 5 minutos para detectar 
          y cerrar órdenes aplicables de forma automática.
        - Permite definir una fecha de inicio opcional para procesar solo órdenes posteriores.
        - Ejecuta con validaciones de seguridad y control de errores.
        
        Usos:
        - Automatizar cierre de órdenes sin intervención manual.
        - Acelerar el ciclo de producción eliminando tareas administrativas.
        - Mantener control parcial mediante fecha de inicio configurada.
    """,
    "data": [
        "views/stock_picking_type_views.xml",
        "data/ir_cron.xml",
    ],
    "application": False,
    "installable": True,
}
