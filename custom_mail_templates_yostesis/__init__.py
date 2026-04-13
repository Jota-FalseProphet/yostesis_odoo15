from odoo import api, SUPERUSER_ID
from .data.translations_data import TRANSLATIONS


def post_init_hook(cr, registry):
    """Apply EN/IT/FR/DE translations to the 10 Yostesis mail templates.

    Writes via env['mail.template'].with_context(lang=...).write({...}) so that
    Odoo handles ir_translation rows through its standard ORM flow (UPDATE of
    the auto-created rows, no INSERT, no unique-constraint collision).

    Only touches subject/body_html of res_ids of these 10 templates.
    """
    env = api.Environment(cr, SUPERUSER_ID, {})
    active_lang_codes = set(env['res.lang'].with_context(active_test=False)
                            .search([('active', '=', True)]).mapped('code'))
    for xmlid, by_lang in TRANSLATIONS.items():
        tpl = env.ref(xmlid, raise_if_not_found=False)
        if not tpl:
            continue
        for lang, vals in by_lang.items():
            if lang not in active_lang_codes:
                # Skip languages that aren't activated in this database.
                continue
            tpl.with_context(lang=lang).write(vals)
