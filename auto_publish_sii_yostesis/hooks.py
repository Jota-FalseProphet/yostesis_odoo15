# auto_publish_sii_yostesis/hooks.py

def pre_init_sii_company(cr):
    """Creamos en SQL las columnas que las vistas de AEAT esperan."""
    # sii_period
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS sii_period VARCHAR
    """)
    # sii_auto_upload (o cualquier otro campo que diga el error)
    cr.execute("""
        ALTER TABLE res_company
        ADD COLUMN IF NOT EXISTS sii_auto_upload BOOLEAN DEFAULT FALSE
    """)
