# -*- coding: utf-8 -*-
{
    "name": "Sale Commission DownPayment (Yostesis)",
    "version": "15.0.1.0.0",
    "summary": "Genera líneas de comisión correctas en facturas de anticipo",
    "description": """
        Corrige el flujo del módulo OCA sale_commission para soportar anticipos:
        * Al crear/validar una factura de anticipo, vuelve a generar las líneas de comisión
          (`account.invoice.line.agent`) una vez existe la línea de anticipo.
        * Elimina líneas de comisión huérfanas y crea las definitivas con `object_id` válido,
          evitando la violación NOT NULL que bloqueaba la facturación.
        * Mantiene el cálculo estándar de comisión para que los agentes cobren sobre el importe
          anticipado, sin perder trazabilidad.
    """,
    "author": "Yostesis",
    "website": "Yostesis",
    "maintainers": ["Yostesis"],
    "depends": [
        "sale_commission", 
        "sale_management",
        "sale_advance_payment",
    ],
    "data": [],
    "application": False,
    "installable": True,
}
