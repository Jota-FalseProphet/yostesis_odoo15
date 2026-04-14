from .hooks import post_init


def _post_init_create_all(cr, registry):
    post_init.run(cr, registry)
