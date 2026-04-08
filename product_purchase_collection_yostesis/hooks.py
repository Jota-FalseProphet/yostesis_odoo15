import csv
import os
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)


def _post_init_load_purchase_collections(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})

    csv_path = os.path.join(
        os.path.dirname(__file__), 'data', 'purchase_collection_data.csv'
    )

    collection_values = set()
    mappings = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            value = row['purchase_collection']
            collection_values.add(value)
            mappings.append((row['external_id'], value))

    PurchaseCollection = env['purchase.collection']
    value_to_id = {}
    for val in sorted(collection_values):
        rec = PurchaseCollection.create({'name': val})
        value_to_id[val] = rec.id

    IrModelData = env['ir.model.data']
    value_to_ext_ids = {}
    for ext_id, val in mappings:
        value_to_ext_ids.setdefault(val, []).append(ext_id)

    total_updated = 0
    total_missing = 0

    for val, ext_id_names in value_to_ext_ids.items():
        data_records = IrModelData.search([
            ('module', '=', '__export__'),
            ('model', '=', 'product.template'),
            ('name', 'in', ext_id_names),
        ])

        product_ids = data_records.mapped('res_id')
        found = len(product_ids)
        missing = len(ext_id_names) - found

        if product_ids:
            env['product.template'].browse(product_ids).write({
                'purchase_collection': value_to_id[val],
            })
            total_updated += found

        if missing:
            total_missing += missing

    _logger.info(
        "Purchase Collection: %d records created, %d products updated, %d external IDs not found",
        len(value_to_id), total_updated, total_missing,
    )
