{
    "name": "PuntMobles - Agrupación de Órdenes de Fabricación",
    "version": "15.0.1.5.8",
    "category": "Manufacturing",
    "summary": "Agrupar OF con criterios y permitir incluir/quitar OF de una agrupación",
    "depends": ["web", "mrp", "product_attributes_type", "sale"],

    "data": [
        "security/security.xml",
        "security/ir.model.access.csv",
        "data/ir_sequence.xml",
        "data/server_actions.xml",
        "views/mrp_productionANDworkorder_agof_views.xml",
        "views/mrp_production_group_views.xml",
        "views/mrp_production_views.xml",
        "views/mrp_production_group_add_wizard_views.xml",
        "views/stock_picking_views.xml",
        "views/stock_picking_type_views.xml",
       # "views/mrp_production_filter_wizard_button_assets.xml",
    ],
    
    "assets": {
        "web.assets_backend": [
            "pmx_mrp_production_group_yostesis/static/src/js/mrp_production_filter_wizard_button.js",
            # "pmx_mrp_production_group_yostesis/static/src/js/pmx_code_prefix_chips.js",
            "pmx_mrp_production_group_yostesis/static/src/js/mrp_production_preselect_owl.js",
            "pmx_mrp_production_group_yostesis/static/src/scss/mrp_production_group_add_wizard.scss",
            # "pmx_mrp_production_group_yostesis/static/src/scss/pmx_code_prefix_chips.scss"
        ],
    },
    "installable": True,
    "application": False,
}
