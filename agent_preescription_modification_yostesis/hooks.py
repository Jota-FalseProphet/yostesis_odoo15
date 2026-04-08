import logging
from lxml import etree

_logger = logging.getLogger(__name__)


def post_init_hook(cr, registry):
    """Hide the Studio field x_studio_many2one_field_4zmRf in sale.order form."""
    cr.execute("""
        SELECT id, arch_db
        FROM ir_ui_view
        WHERE model = 'sale.order'
          AND arch_db LIKE '%%x_studio_many2one_field_4zmRf%%'
          AND name LIKE '%%Studio%%'
        LIMIT 1
    """)
    row = cr.fetchone()
    if not row:
        _logger.info("Studio view with x_studio_many2one_field_4zmRf not found, skipping.")
        return

    view_id, arch_db = row
    root = etree.fromstring(arch_db.encode('utf-8'))

    for field_node in root.iter('field'):
        if field_node.get('name') == 'x_studio_many2one_field_4zmRf':
            field_node.set('invisible', '1')
            _logger.info("Hidden x_studio_many2one_field_4zmRf in Studio view %s", view_id)
            break

    new_arch = etree.tostring(root, encoding='unicode', xml_declaration=False)
    cr.execute("UPDATE ir_ui_view SET arch_db = %s WHERE id = %s", (new_arch, view_id))
