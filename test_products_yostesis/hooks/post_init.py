# -*- coding: utf-8 -*-
"""Post-install hook for test_products_yostesis.

Crea partners, workcenters, atributos, valores de atributo, 28 product.template
con sus attribute_lines + rutas + seller, 88 variantes con default_code
originales, y 13 mrp.bom (normal/phantom/subcontract) con líneas, filtros por
variante, operaciones de ruta y subcontratistas.

Todo con estrategia buscar-o-crear por nombre/código → idempotente.
"""
import logging

from odoo import SUPERUSER_ID, api

_logger = logging.getLogger(__name__)
MOD = "test_products_yostesis"


# ============================================================================
# DATOS
# ============================================================================

PARTNERS = [
    ("proveedor_crudos", "*PROVEEDOR DE CRUDOS"),
    ("subcontratista_anodizados", "*SUBCONTRATISTA ANODIZADOS"),
    ("subcontratista_pulimento", "*SUBCONTRATISTA PULIMENTO"),
    ("proveedor_ferreteria", "*PROVEEDOR FERRETERIA"),
    ("subcontratista_montaje", "*SUBCONTRATISTA MONTAJE"),
    ("proveedor_aluminios", "*PROVEEDOR DE ALUMINIOS"),
]

WORKCENTERS = [
    ("wc_cabina_pintado", "CABINA DE PINTADO", "CT01"),
    ("wc_cnc", "CENTRO MECANIZADO CNC", "CT04"),
]

# attr_key -> (name, display_type, create_variant, sequence)
ATTRIBUTES = [
    ("lxdxh", "LxDxH MODULO", "radio", "dynamic", 0),
    ("module", "MODULE", "radio", "dynamic", 1),
    ("colour", "BASE COLOUR", "radio", "dynamic", 14),
]

# attr_key -> [(val_key, name, sequence, html_color)]
ATTRIBUTE_VALUES = {
    "lxdxh": [
        ("71x16x71", "71x16x71", None, None),
    ],
    "module": [
        ("smo", "SUPER MATT OAK", 0, "#F2AE69"),
        ("wso", "WALNUT STAINED OAK", 2, "#472717"),
        ("who", "WHITENED OAK", 4, "#CAA97F"),
        ("smw", "SUPER MATT WALNUT", 5, "#A15F3C"),
        ("bsw", "BLACK STAINED WALNUT", 6, "#141311"),
        ("wsw", "WALNUT STAINED WALNUT", 8, "#482717"),
    ],
    "colour": [
        ("nat", "ANODIZADO NATURAL", 26, None),
        ("neg", "ANODIZADO NEGRO", 27, None),
    ],
}

# route_key -> Odoo XID
ROUTES = {
    "mto": "stock.route_warehouse0_mto",
    "manufacture": "mrp.route_warehouse0_manufacture",
    "buy": "purchase_stock.route_warehouse0_buy",
    "resupply": "mrp_subcontracting.route_resupply_subcontractor_mto",
}

# Templates: tmpl_key -> dict
TEMPLATES = {
    "pv_fab_01_simple": {
        "name": "*PRODUCTO DE VENTA FAB 01 (SIMPLE)", "default_code": None,
        "sale_ok": True, "purchase_ok": False, "produce_delay": 2,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture"],
        "attributes": [("lxdxh", ["71x16x71"]),
                       ("module", ["smo", "wso", "who", "smw", "bsw", "wsw"]),
                       ("colour", ["nat", "neg"])],
        "seller": None,
    },
    "pv_fab_02": {
        "name": "*PRODUCTO DE VENTA FAB 02", "default_code": None,
        "sale_ok": True, "purchase_ok": False, "produce_delay": 2,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture"],
        "attributes": [("lxdxh", ["71x16x71"]),
                       ("module", ["smo", "wso", "who", "smw", "bsw", "wsw"]),
                       ("colour", ["nat", "neg"])],
        "seller": None,
    },
    "pv_fab_03": {
        "name": "*PRODUCTO DE VENTA FAB 03", "default_code": None,
        "sale_ok": True, "purchase_ok": False, "produce_delay": 2,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture"],
        "attributes": [("lxdxh", ["71x16x71"]),
                       ("module", ["smo", "wso", "who", "smw", "bsw", "wsw"]),
                       ("colour", ["nat", "neg"])],
        "seller": None,
    },
    "pv_sub_04": {
        "name": "*PRODUCTO DE VENTA SUB 04", "default_code": None,
        "sale_ok": True, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [("lxdxh", ["71x16x71"]),
                       ("module", ["smo", "wso", "who", "smw", "bsw", "wsw"]),
                       ("colour", ["nat", "neg"])],
        "seller": "subcontratista_montaje",
    },
    "pv_sub_05_simple": {
        "name": "*PRODUCTO DE VENTA SUB 05 (SIMPLE)", "default_code": None,
        "sale_ok": True, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [("lxdxh", ["71x16x71"]),
                       ("module", ["smo", "wso", "who", "smw", "bsw", "wsw"]),
                       ("colour", ["nat", "neg"])],
        "seller": "subcontratista_montaje",
    },
    "pulimentado_fab_01": {
        "name": "*PULIMENTADO FAB 01", "default_code": None,
        "sale_ok": False, "purchase_ok": False, "produce_delay": 3,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture", "resupply"],
        "attributes": [("module", ["smo", "wso", "who", "smw", "bsw", "wsw"])],
        "seller": None,
    },
    "pulimentado_fab_02": {
        "name": "*PULIMENTADO FAB 02", "default_code": None,
        "sale_ok": False, "purchase_ok": False, "produce_delay": 3,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture", "resupply"],
        "attributes": [("module", ["smo", "wso", "who", "smw", "bsw", "wsw"])],
        "seller": None,
    },
    "pulimentado_sub_03": {
        "name": "*PULIMENTADO SUB 03", "default_code": None,
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy", "resupply"],
        "attributes": [("module", ["smo", "wso", "who", "smw", "bsw", "wsw"])],
        "seller": "subcontratista_pulimento",
    },
    "conjunto_pulimentado": {
        "name": "*CONJUNTO PULIMENTADO", "default_code": None,
        "sale_ok": False, "purchase_ok": False, "produce_delay": 3,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": [],
        "attributes": [("module", ["smo", "wso", "who", "smw", "bsw", "wsw"])],
        "seller": None,
    },
    "anodizado_sub_01": {
        "name": "*ANODIZADO SUB 01", "default_code": None,
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [("colour", ["nat", "neg"])],
        "seller": "subcontratista_anodizados",
    },
    "mec_nog_fab_03": {
        "name": "*MECANIZADO NOG FAB 03", "default_code": "MEC-NOG03",
        "sale_ok": False, "purchase_ok": False, "produce_delay": 3,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture", "resupply"],
        "attributes": [], "seller": None,
    },
    "mec_rob_fab_03": {
        "name": "*MECANIZADO ROB FAB 03", "default_code": "MEC-ROB03",
        "sale_ok": False, "purchase_ok": False, "produce_delay": 3,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "manufacture", "resupply"],
        "attributes": [], "seller": None,
    },
    "cru_rob_01": {
        "name": "*CRUDO ROBLE 01", "default_code": "CRU-ROB01",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "cru_rob_02": {
        "name": "*CRUDO ROBLE 02", "default_code": "CRU-ROB02",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "cru_rob_03": {
        "name": "*CRUDO ROBLE 03", "default_code": "CRU-ROB03",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "cru_nog_01": {
        "name": "*CRUDO NOGAL 01", "default_code": "CRU-NOG01",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "cru_nog_02": {
        "name": "*CRUDO NOGAL 02", "default_code": "CRU-NOG02",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "cru_nog_03": {
        "name": "*CRUDO NOGAL 03", "default_code": "CRU-NOG03",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_crudos",
    },
    "aluminio_01": {
        "name": "*ALUMINIO 01", "default_code": "ALU01",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy", "resupply"],
        "attributes": [], "seller": "proveedor_aluminios",
    },
    "herraje_01": {
        "name": "*HERRAJE 01", "default_code": "HER01",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 1.0,
    },
    "herraje_02": {
        "name": "*HERRAJE 02", "default_code": "HER02",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 1.0,
    },
    "herraje_03": {
        "name": "*HERRAJE 03", "default_code": "HER03",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 0.0,
    },
    "herraje_04": {
        "name": "*HERRAJE 04", "default_code": "HER04",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 1.0,
    },
    "herraje_05": {
        "name": "*HERRAJE 05", "default_code": "HER05",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 1.0,
    },
    "herraje_06": {
        "name": "*HERRAJE 06", "default_code": "HER06",
        "sale_ok": False, "purchase_ok": True, "produce_delay": 0,
        "invoice_policy": "delivery", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": "proveedor_ferreteria", "seller_price": 1.0,
    },
    "conjunto_herraje_1_3": {
        "name": "*CONJUNTO HERRAJE 1-3", "default_code": "CONJ-HER1-3",
        "sale_ok": False, "purchase_ok": False, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": None,
    },
    "conjunto_herraje_4_6": {
        "name": "*CONJUNTO HERRAJE 4-6", "default_code": "CONJ-HER4-6",
        "sale_ok": False, "purchase_ok": False, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": None,
    },
    "conjunto_herrajes_todo": {
        "name": "*CONJUNTO HERRAJES TODO", "default_code": "CONJ-HER",
        "sale_ok": False, "purchase_ok": False, "produce_delay": 0,
        "invoice_policy": "order", "purchase_method": "receive",
        "routes": ["mto", "buy"],
        "attributes": [], "seller": None,
    },
}

# Variantes: tmpl_key -> [(combo_val_names, default_code)]
VARIANT_MAPS = {
    "pv_fab_01_simple": [
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NATURAL"), "PV01-00001"),
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NEGRO"), "PV01-00006"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NATURAL"), "PV01-00007"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NEGRO"), "PV01-00008"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NATURAL"), "PV01-00009"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NEGRO"), "PV01-00010"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NATURAL"), "PV01-00011"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NEGRO"), "PV01-00012"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NATURAL"), "PV01-00002"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NEGRO"), "PV01-00003"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NATURAL"), "PV01-00004"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NEGRO"), "PV01-00005"),
    ],
    "pv_fab_02": [
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NATURAL"), "PV02-00001"),
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NEGRO"), "PV02-00002"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NATURAL"), "PV02-00003"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NEGRO"), "PV02-00004"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NATURAL"), "PV02-00005"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NEGRO"), "PV02-00006"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NATURAL"), "PV02-00007"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NEGRO"), "PV02-00008"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NATURAL"), "PV02-00009"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NEGRO"), "PV02-00010"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NATURAL"), "PV02-00011"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NEGRO"), "PV02-00012"),
    ],
    "pv_fab_03": [
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NATURAL"), "PV03-00001"),
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NEGRO"), "PV03-00002"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NATURAL"), "PV03-00003"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NEGRO"), "PV03-00004"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NATURAL"), "PV03-00005"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NEGRO"), "PV03-00006"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NATURAL"), "PV03-00007"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NEGRO"), "PV03-00008"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NATURAL"), "PV03-00009"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NEGRO"), "PV03-00010"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NATURAL"), "PV03-00011"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NEGRO"), "PV03-00012"),
    ],
    "pv_sub_04": [
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NATURAL"), "PV04-00001"),
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NEGRO"), "PV04-00002"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NATURAL"), "PV04-00003"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NEGRO"), "PV04-00004"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NATURAL"), "PV04-00005"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NEGRO"), "PV04-00006"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NATURAL"), "PV04-00007"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NEGRO"), "PV04-00008"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NATURAL"), "PV04-00009"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NEGRO"), "PV04-00010"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NATURAL"), "PV04-00011"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NEGRO"), "PV04-00012"),
    ],
    "pv_sub_05_simple": [
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NATURAL"), "PV05-00001"),
        (("71x16x71", "SUPER MATT OAK", "ANODIZADO NEGRO"), "PV05-00002"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NATURAL"), "PV05-00003"),
        (("71x16x71", "WALNUT STAINED OAK", "ANODIZADO NEGRO"), "PV05-00004"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NATURAL"), "PV05-00005"),
        (("71x16x71", "WHITENED OAK", "ANODIZADO NEGRO"), "PV05-00006"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NATURAL"), "PV05-00007"),
        (("71x16x71", "SUPER MATT WALNUT", "ANODIZADO NEGRO"), "PV05-00008"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NATURAL"), "PV05-00009"),
        (("71x16x71", "BLACK STAINED WALNUT", "ANODIZADO NEGRO"), "PV05-00010"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NATURAL"), "PV05-00011"),
        (("71x16x71", "WALNUT STAINED WALNUT", "ANODIZADO NEGRO"), "PV05-00012"),
    ],
    "pulimentado_fab_01": [
        (("SUPER MATT OAK",), "PUL01-00001"),
        (("WALNUT STAINED OAK",), "PUL01-00005"),
        (("WHITENED OAK",), "PUL01-00006"),
        (("SUPER MATT WALNUT",), "PUL01-00002"),
        (("BLACK STAINED WALNUT",), "PUL01-00003"),
        (("WALNUT STAINED WALNUT",), "PUL01-00004"),
    ],
    "pulimentado_fab_02": [
        (("SUPER MATT OAK",), "PUL02-00001"),
        (("WALNUT STAINED OAK",), "PUL02-00002"),
        (("WHITENED OAK",), "PUL02-00003"),
        (("SUPER MATT WALNUT",), "PUL02-00004"),
        (("BLACK STAINED WALNUT",), "PUL02-00005"),
        (("WALNUT STAINED WALNUT",), "PUL02-00006"),
    ],
    "pulimentado_sub_03": [
        (("SUPER MATT OAK",), "PUL03-00001"),
        (("WALNUT STAINED OAK",), "PUL03-00002"),
        (("WHITENED OAK",), "PUL03-00003"),
        (("SUPER MATT WALNUT",), "PUL03-00004"),
        (("BLACK STAINED WALNUT",), "PUL03-00005"),
        (("WALNUT STAINED WALNUT",), "PUL03-00006"),
    ],
    "conjunto_pulimentado": [
        (("SUPER MATT OAK",), "KIT-PUL-00001"),
        (("WALNUT STAINED OAK",), "KIT-PUL-00002"),
        (("WHITENED OAK",), "KIT-PUL-00003"),
        (("SUPER MATT WALNUT",), "KIT-PUL-00004"),
        (("BLACK STAINED WALNUT",), "KIT-PUL-00005"),
        (("WALNUT STAINED WALNUT",), "KIT-PUL-00006"),
    ],
    "anodizado_sub_01": [
        (("ANODIZADO NATURAL",), "ANO01-00002"),
        (("ANODIZADO NEGRO",), "ANO01-00003"),
    ],
}

# BoMs
BOMS = [
    {"tmpl": "cru_rob_03", "type": "normal", "subcontractor": None,
     "components": [{"tmpl": "cru_rob_03", "qty": 1.0, "seq": 1, "filter": None}],
     "routings": [{"wc": "wc_cnc", "name": "Mecanizado", "seq": 103}]},
    {"tmpl": "cru_nog_03", "type": "normal", "subcontractor": None,
     "components": [{"tmpl": "cru_nog_03", "qty": 1.0, "seq": 1, "filter": None}],
     "routings": [{"wc": "wc_cnc", "name": "Mecanizado", "seq": 103}]},
    {"tmpl": "cru_nog_01", "type": "normal", "subcontractor": None,
     "components": [
         {"tmpl": "cru_nog_01", "qty": 1.0, "seq": 1,
          "filter": {"tmpl": "pulimentado_fab_01",
                     "values": ["SUPER MATT WALNUT", "BLACK STAINED WALNUT", "WALNUT STAINED WALNUT"]}},
         {"tmpl": "cru_rob_01", "qty": 1.0, "seq": 1,
          "filter": {"tmpl": "pulimentado_fab_01",
                     "values": ["SUPER MATT OAK", "WALNUT STAINED OAK", "WHITENED OAK"]}},
     ],
     "routings": [{"wc": "wc_cabina_pintado", "name": "Pulimentado", "seq": 104}]},
    {"tmpl": "cru_nog_02", "type": "normal", "subcontractor": None,
     "components": [
         {"tmpl": "cru_nog_02", "qty": 1.0, "seq": 1,
          "filter": {"tmpl": "pulimentado_fab_02",
                     "values": ["SUPER MATT WALNUT", "BLACK STAINED WALNUT", "WALNUT STAINED WALNUT"]}},
         {"tmpl": "cru_rob_02", "qty": 1.0, "seq": 1,
          "filter": {"tmpl": "pulimentado_fab_02",
                     "values": ["SUPER MATT OAK", "WALNUT STAINED OAK", "WHITENED OAK"]}},
     ],
     "routings": [{"wc": "wc_cabina_pintado", "name": "Pulimentado", "seq": 104}]},
    {"tmpl": "mec_nog_fab_03", "type": "normal", "subcontractor": "subcontratista_pulimento",
     "components": [
         {"tmpl": "mec_nog_fab_03", "qty": 1.0, "seq": 1,
          "filter": {"tmpl": "pulimentado_sub_03",
                     "values": ["SUPER MATT WALNUT", "BLACK STAINED WALNUT", "WALNUT STAINED WALNUT"]}},
         {"tmpl": "mec_rob_fab_03", "qty": 1.0, "seq": 2,
          "filter": {"tmpl": "pulimentado_sub_03",
                     "values": ["SUPER MATT OAK", "WALNUT STAINED OAK", "WHITENED OAK"]}},
     ], "routings": []},
    {"tmpl": "conjunto_pulimentado", "type": "phantom", "subcontractor": None,
     "components": [], "routings": []},
    {"tmpl": "pv_sub_04", "type": "subcontract", "subcontractor": "subcontratista_montaje",
     "components": [], "routings": []},
    {"tmpl": "anodizado_sub_01", "type": "subcontract", "subcontractor": "subcontratista_anodizados",
     "components": [{"tmpl": "aluminio_01", "qty": 1.0, "seq": 1, "filter": None}],
     "routings": []},
    {"tmpl": "conjunto_herraje_1_3", "type": "phantom", "subcontractor": None,
     "components": [
         {"tmpl": "herraje_01", "qty": 1.0, "seq": 1, "filter": None},
         {"tmpl": "herraje_02", "qty": 1.0, "seq": 1, "filter": None},
         {"tmpl": "herraje_03", "qty": 1.0, "seq": 1, "filter": None},
     ], "routings": []},
    {"tmpl": "conjunto_herraje_4_6", "type": "phantom", "subcontractor": None,
     "components": [
         {"tmpl": "herraje_04", "qty": 1.0, "seq": 1, "filter": None},
         {"tmpl": "herraje_05", "qty": 1.0, "seq": 1, "filter": None},
         {"tmpl": "herraje_06", "qty": 1.0, "seq": 1, "filter": None},
     ], "routings": []},
    {"tmpl": "conjunto_herrajes_todo", "type": "phantom", "subcontractor": None,
     "components": [
         {"tmpl": "conjunto_herraje_1_3", "qty": 1.0, "seq": 1, "filter": None},
         {"tmpl": "conjunto_herraje_4_6", "qty": 1.0, "seq": 1, "filter": None},
     ], "routings": []},
    {"tmpl": "pv_fab_01_simple", "type": "normal", "subcontractor": None,
     "components": [], "routings": []},
    {"tmpl": "pv_sub_05_simple", "type": "subcontract", "subcontractor": "subcontratista_montaje",
     "components": [], "routings": []},
]


# ============================================================================
# Helpers buscar-o-crear
# ============================================================================

def _ensure_partners(env):
    out = {}
    for key, name in PARTNERS:
        p = env["res.partner"].search([("name", "=", name), ("is_company", "=", True)], limit=1)
        if not p:
            p = env["res.partner"].create({"name": name, "is_company": True, "supplier_rank": 1})
            _logger.info("[%s] Partner creado: %s", MOD, name)
        else:
            if p.supplier_rank < 1:
                p.supplier_rank = 1
        out[key] = p
    return out


def _ensure_workcenters(env):
    out = {}
    for key, name, code in WORKCENTERS:
        wc = env["mrp.workcenter"].search([("code", "=", code)], limit=1)
        if not wc:
            wc = env["mrp.workcenter"].search([("name", "=", name)], limit=1)
        if not wc:
            wc = env["mrp.workcenter"].create({
                "name": name, "code": code,
                "time_efficiency": 100, "capacity": 1,
            })
            _logger.info("[%s] Workcenter creado: %s (%s)", MOD, name, code)
        out[key] = wc
    return out


def _ensure_attributes(env):
    attrs, vals = {}, {}
    for key, name, display, create_variant, seq in ATTRIBUTES:
        a = env["product.attribute"].search([("name", "=", name)], limit=1)
        if not a:
            a = env["product.attribute"].create({
                "name": name, "display_type": display,
                "create_variant": create_variant, "sequence": seq,
            })
            _logger.info("[%s] Atributo creado: %s", MOD, name)
        attrs[key] = a
    for attr_key, val_list in ATTRIBUTE_VALUES.items():
        for val_key, val_name, val_seq, html_color in val_list:
            v = env["product.attribute.value"].search([
                ("attribute_id", "=", attrs[attr_key].id),
                ("name", "=", val_name),
            ], limit=1)
            if not v:
                vals_dict = {"attribute_id": attrs[attr_key].id, "name": val_name}
                if val_seq is not None:
                    vals_dict["sequence"] = val_seq
                if html_color:
                    vals_dict["html_color"] = html_color
                v = env["product.attribute.value"].create(vals_dict)
                _logger.info("[%s] Valor creado: %s / %s", MOD, attrs[attr_key].name, val_name)
            vals[(attr_key, val_key)] = v
    return attrs, vals


def _ensure_routes(env):
    out = {}
    for key, xid in ROUTES.items():
        try:
            out[key] = env.ref(xid)
        except ValueError:
            _logger.warning("[%s] Ruta %s (%s) no encontrada — se omitirá.", MOD, key, xid)
            out[key] = None
    return out


def _ensure_template(env, tmpl_key, data, partners, attrs, vals, routes):
    """Crea o reutiliza un product.template."""
    dom = [("name", "=", data["name"])]
    if data.get("default_code"):
        dom = ["|", ("default_code", "=", data["default_code"])] + dom
    t = env["product.template"].search(dom, limit=1)
    if t:
        _logger.info("[%s] Template ya existe: %s (id=%s) — se reutiliza.", MOD, data["name"], t.id)
        return t

    attribute_line_ids = []
    for attr_key, val_keys in data["attributes"]:
        attribute_line_ids.append((0, 0, {
            "attribute_id": attrs[attr_key].id,
            "value_ids": [(6, 0, [vals[(attr_key, vk)].id for vk in val_keys])],
        }))

    route_ids = [routes[r].id for r in data["routes"] if routes.get(r)]

    vals_tmpl = {
        "name": data["name"],
        "detailed_type": "product",
        "sale_ok": data["sale_ok"],
        "purchase_ok": data["purchase_ok"],
        "list_price": 1.0,
        "produce_delay": data["produce_delay"],
        "invoice_policy": data["invoice_policy"],
        "purchase_method": data["purchase_method"],
    }
    if data.get("default_code"):
        vals_tmpl["default_code"] = data["default_code"]
    if attribute_line_ids:
        vals_tmpl["attribute_line_ids"] = attribute_line_ids
    if route_ids:
        vals_tmpl["route_ids"] = [(6, 0, route_ids)]
    if data.get("seller"):
        partner = partners[data["seller"]]
        vals_tmpl["seller_ids"] = [(0, 0, {
            "name": partner.id,
            "price": data.get("seller_price", 1.0),
            "min_qty": data.get("seller_min_qty", 1.0),
            "delay": data.get("seller_delay", 10),
            "sequence": 1,
        })]

    t = env["product.template"].create(vals_tmpl)
    _logger.info("[%s] Template creado: %s (id=%s)", MOD, data["name"], t.id)
    return t


def _ensure_templates(env, partners, attrs, vals, routes):
    out = {}
    for tmpl_key, data in TEMPLATES.items():
        out[tmpl_key] = _ensure_template(env, tmpl_key, data, partners, attrs, vals, routes)
    return out


def _get_or_create_variant(env, tmpl, combo_names):
    ptavs = env["product.template.attribute.value"].search([
        ("product_tmpl_id", "=", tmpl.id),
        ("name", "in", list(combo_names)),
    ])
    if len(ptavs) != len(combo_names):
        _logger.warning("[%s] %s: faltan PTAV para combo %s (match=%s)",
                        MOD, tmpl.display_name, combo_names, ptavs.mapped("name"))
    variant = tmpl._create_product_variant(ptavs)
    if not variant:
        variant = env["product.product"].search([
            ("product_tmpl_id", "=", tmpl.id),
            ("product_template_attribute_value_ids", "=", ptavs.ids),
        ], limit=1)
    return variant


def _single_variant(env, tmpl):
    return env["product.product"].search([("product_tmpl_id", "=", tmpl.id)], limit=1)


def _create_variants(env, templates):
    _logger.info("[%s] Forzando creación de variantes con default_code…", MOD)
    for tmpl_key, combos in VARIANT_MAPS.items():
        tmpl = templates.get(tmpl_key)
        if not tmpl:
            continue
        for combo_names, code in combos:
            v = _get_or_create_variant(env, tmpl, combo_names)
            if v:
                if v.default_code != code:
                    v.default_code = code


def _resolve_filter_ptavs(env, templates, tmpl_key, value_names):
    tmpl = templates.get(tmpl_key)
    if not tmpl:
        return env["product.template.attribute.value"]
    return env["product.template.attribute.value"].search([
        ("product_tmpl_id", "=", tmpl.id),
        ("name", "in", list(value_names)),
    ])


def _create_boms(env, templates, partners, workcenters):
    _logger.info("[%s] Creando mrp.bom…", MOD)
    uom_unit = env.ref("uom.product_uom_unit")
    for bom_data in BOMS:
        tmpl = templates.get(bom_data["tmpl"])
        if not tmpl:
            continue
        exists = env["mrp.bom"].search([
            ("product_tmpl_id", "=", tmpl.id),
            ("code", "=", "*PRUEBAS"),
        ], limit=1)
        if exists:
            continue

        vals = {
            "code": "*PRUEBAS",
            "product_tmpl_id": tmpl.id,
            "product_qty": 1.0,
            "product_uom_id": uom_unit.id,
            "type": bom_data["type"],
            "consumption": "warning",
        }
        if bom_data["subcontractor"]:
            vals["subcontractor_ids"] = [(6, 0, [partners[bom_data["subcontractor"]].id])]
        bom = env["mrp.bom"].create(vals)

        for comp in bom_data["components"]:
            comp_tmpl = templates.get(comp["tmpl"])
            if not comp_tmpl:
                continue
            comp_product = _single_variant(env, comp_tmpl)
            if not comp_product:
                _logger.warning("[%s] Sin variante para componente %s", MOD, comp["tmpl"])
                continue
            line_vals = {
                "bom_id": bom.id,
                "product_id": comp_product.id,
                "product_qty": comp["qty"],
                "product_uom_id": uom_unit.id,
                "sequence": comp["seq"],
            }
            if comp["filter"]:
                ptavs = _resolve_filter_ptavs(env, templates, comp["filter"]["tmpl"], comp["filter"]["values"])
                if ptavs:
                    line_vals["bom_product_template_attribute_value_ids"] = [(6, 0, ptavs.ids)]
            env["mrp.bom.line"].create(line_vals)

        for routing in bom_data["routings"]:
            wc = workcenters.get(routing["wc"])
            if not wc:
                continue
            env["mrp.routing.workcenter"].create({
                "bom_id": bom.id,
                "workcenter_id": wc.id,
                "name": routing["name"],
                "sequence": routing["seq"],
                "time_cycle_manual": 0,
                "time_mode": "manual",
            })


def run(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    _logger.info("[%s] Inicio post-init.", MOD)
    partners = _ensure_partners(env)
    workcenters = _ensure_workcenters(env)
    attrs, vals = _ensure_attributes(env)
    routes = _ensure_routes(env)
    templates = _ensure_templates(env, partners, attrs, vals, routes)
    _create_variants(env, templates)
    _create_boms(env, templates, partners, workcenters)
    _logger.info("[%s] Post-init completado.", MOD)
