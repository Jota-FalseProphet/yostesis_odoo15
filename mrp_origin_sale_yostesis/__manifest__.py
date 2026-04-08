{
    "name": "MRP Origin Sale (Yostesis)",
    "version": "15.0.2.3.1",
    "summary": "Stored origin_sale/origin_purchase on MOs with recompute on confirm and receipt validation",
    "author": "Yostesis",
    "website": "https://yostesis.com",
    "license": "LGPL-3",
    "depends": [
        "mrp",
        "sale_mrp",
        "mrp_subcontracting",
        "purchase",
        "indaws_internal_reference",
        "pmx_mrp_production_group_yostesis",
        "custom_fields_puntmobles_yostesis",
    ],
    "data": [
        "views/mrp_production_views.xml",
        "views/mrp_production_group_add_wizard_views.xml",
    ],
    "application": False,
    "installable": True,
}
