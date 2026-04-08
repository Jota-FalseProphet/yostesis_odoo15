from odoo import api, SUPERUSER_ID


def migrate(cr, version):
    env = api.Environment(cr, SUPERUSER_ID, {})

    cr.execute("""
        SELECT DISTINCT CAST(purchase_collection_old AS TEXT)
        FROM product_template
        WHERE purchase_collection_old IS NOT NULL
          AND CAST(purchase_collection_old AS TEXT) != ''
    """)
    old_values = [row[0] for row in cr.fetchall()]

    PurchaseCollection = env['purchase.collection']
    for val in old_values:
        rec = PurchaseCollection.create({'name': val})
        cr.execute(
            "UPDATE product_template SET purchase_collection = %s "
            "WHERE CAST(purchase_collection_old AS TEXT) = %s",
            (rec.id, val),
        )

    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'product_template' AND column_name = 'purchase_collection_old'
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE product_template DROP COLUMN purchase_collection_old")
