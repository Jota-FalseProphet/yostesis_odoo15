# Copyright 2024 Sodexis
# License OPL-1 (See LICENSE file for full copyright and licensing details).

def post_init_hook(cr, registry):
    """Populate route_ids from product template to its variants(product_product)
    """
    query = """
        with product_rel as (
        select 
        srp.product_id as product_tmpl_id, srp.route_id, pp.id as product_id
        from
        stock_route_product srp,
        product_product pp,
        product_template pt
        where 
        srp.product_id = pp.product_tmpl_id
        and pt.id = pp.product_tmpl_id
        and pt.detailed_type in ('product', 'consu')
        )
        insert into product_routes_rel (product_id, route_id) select product_id, route_id from product_rel on conflict do nothing;"""
    cr.execute(query)
