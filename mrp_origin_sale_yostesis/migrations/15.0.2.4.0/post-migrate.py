import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    cr.execute("SELECT COUNT(*) FROM mrp_production")
    total = cr.fetchone()[0]
    _logger.info(
        "Recomputing origin_date_expected for %d MOs...", total,
    )

    cr.execute("""
        UPDATE mrp_production mo
        SET origin_date_expected = CASE
            WHEN mo.origin_sale IS NOT NULL
                THEN (SELECT so.commitment_date
                      FROM sale_order so
                      WHERE so.id = mo.origin_sale)
            WHEN mo.origin_purchase_id IS NOT NULL
                THEN (SELECT po.date_planned
                      FROM purchase_order po
                      WHERE po.id = mo.origin_purchase_id)
            WHEN mo.origin_production_id IS NOT NULL
                THEN (SELECT mo2.date_deadline
                      FROM mrp_production mo2
                      WHERE mo2.id = mo.origin_production_id)
            ELSE mo.date_deadline
        END
    """)

    updated = cr.rowcount
    _logger.info("origin_date_expected updated on %d MOs.", updated)
