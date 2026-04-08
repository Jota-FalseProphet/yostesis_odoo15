def migrate(cr, version):
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'product_template' AND column_name = 'purchase_collection'
    """)
    if cr.fetchone():
        cr.execute("ALTER TABLE product_template RENAME COLUMN purchase_collection TO purchase_collection_old")

    cr.execute("""
        DELETE FROM ir_model_fields_selection
        WHERE field_id IN (
            SELECT id FROM ir_model_fields
            WHERE model = 'product.template' AND name = 'purchase_collection'
        )
    """)

    cr.execute("""
        DELETE FROM ir_model_data
        WHERE model = 'ir.model.fields.selection'
          AND res_id NOT IN (SELECT id FROM ir_model_fields_selection)
    """)
