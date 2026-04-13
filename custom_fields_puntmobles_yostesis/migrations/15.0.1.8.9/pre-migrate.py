def migrate(cr, version):
    # Renombrar project_id → sale_project_ref_id en sale_order
    # para liberar el nombre project_id que usa el módulo core sale_project
    # (Many2one a project.project)
    cr.execute("""
        SELECT column_name FROM information_schema.columns
        WHERE table_name = 'sale_order' AND column_name = 'project_id'
    """)
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE sale_order RENAME COLUMN project_id TO sale_project_ref_id"
        )
    cr.execute("""
        SELECT constraint_name FROM information_schema.table_constraints
        WHERE table_name = 'sale_order' AND constraint_name = 'sale_order_project_id_fkey'
    """)
    if cr.fetchone():
        cr.execute(
            "ALTER TABLE sale_order DROP CONSTRAINT sale_order_project_id_fkey"
        )
    # Actualizar la vista heredada en BD para que la validación combinada
    # no falle al encontrar project_id antes de que se cargue la XML nueva
    cr.execute("""
        UPDATE ir_ui_view
        SET arch_db = REPLACE(arch_db, 'name="project_id"', 'name="sale_project_ref_id"')
        WHERE id IN (
            SELECT res_id FROM ir_model_data
            WHERE module = 'custom_fields_puntmobles_yostesis'
              AND name = 'view_order_form_inherit_sale_order_project'
        )
    """)
