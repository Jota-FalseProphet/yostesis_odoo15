from . import models


def _post_init_copy_commitment_to_prevista(cr, registry):
    cr.execute("""
        UPDATE sale_order
        SET fecha_entrega_prevista = commitment_date
        WHERE commitment_date IS NOT NULL
          AND fecha_entrega_prevista IS NULL
    """)
