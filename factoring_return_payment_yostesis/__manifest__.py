{
    "name": "Factoring Return Payment Yostesis",
    "summary": "Redirige las devoluciones de cobro de factoring a la cuenta puente (suspense) del diario bancario.",
    "description": """
        Módulo puente entre account_payment_return y automated_confirming_yostesis.

        Cuando se confirma una devolución de cobro para una factura que pasó por
        factoring, el asiento de devolución acredita la cuenta puente (suspense)
        del diario bancario en lugar de la cuenta bancaria por defecto, permitiendo
        la conciliación manual en el proceso de conciliación bancaria.
    """,
    "license": "AGPL-3",
    "author": "Yostesis",
    "website": "https://yostesis.cloud",
    "category": "Accounting",
    "version": "15.0.3.0.0",
    "depends": [
        "automated_confirming_yostesis",
        "account_payment_return",
        "account_accountant",
    ],
    "data": [],
    "installable": True,
    "auto_install": True,
}
