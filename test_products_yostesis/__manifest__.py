# -*- coding: utf-8 -*-
{
    "name": "Test Products (Yostesis)",
    "version": "15.0.1.0.0",
    "summary": "Recrea los 28 productos de pruebas (prefijo *) de staging con atributos, variantes, proveedores, rutas, listas de materiales y subcontratación.",
    "description": """
Módulo de datos que crea todo el set de productos de pruebas de PuntMobles
(los 28 templates con prefijo `*`) para poder instalarlo en cualquier clon.

Todo se crea vía ``post_init_hook`` con estrategia buscar-o-crear, por lo
que es idempotente y no colisiona con atributos/partners/workcenters ya
existentes en la base.

Incluye:
  * 6 proveedores/subcontratistas.
  * 2 centros de trabajo (CENTRO MECANIZADO CNC, CABINA DE PINTADO).
  * 3 atributos dinámicos (LxDxH MODULO, MODULE, BASE COLOUR) con sus valores.
  * 28 product.template con atributos, variantes forzadas (default_code
    originales), rutas (MTO/Buy/Manufacture/Resupply Subcontractor) y
    proveedores por defecto.
  * 13 mrp.bom (normal, phantom, subcontract) con sus líneas, filtros por
    variante, operaciones de ruta y subcontratistas.
""",
    "author": "Yostesis",
    "website": "https://yostesis.com",
    "maintainers": ["Yostesis"],
    "category": "Tests",
    "license": "LGPL-3",
    "depends": [
        "base",
        "product",
        "stock",
        "purchase",
        "purchase_stock",
        "mrp",
        "mrp_subcontracting",
    ],
    "data": [],
    "post_init_hook": "_post_init_create_all",
    "application": False,
    "installable": True,
}
