{
    'name': "Yostesis - Vendor Proposed Delivery Date (non-destructive)",
    'version': '15.0.1.1.0',
    'author': "Yostesis",
    'website': "https://yostesis.com",
    'category': 'Purchases',
    'license': 'LGPL-3',
    'summary': "Vendors can no longer overwrite the scheduled delivery date "
               "from the portal reminder. Their proposal is stored in a "
               "parallel field for the buyer to review and apply.",
    'description': """
Vendor Proposed Delivery Date
=============================

Native Odoo lets the vendor update `date_planned` on each purchase order line
directly from the reminder email ("No, update the dates" button). That change
is applied silently and overwrites the buyer's planning.

This module keeps the same vendor-facing UX but redirects the write to a new
field so the scheduled date stays under the buyer's control.

What it does
------------
* Adds `date_planned_vendory` (Datetime) on `purchase.order.line` — the date
  proposed by the vendor from the portal.
* Adds `has_vendor_proposed_datesy` (Boolean, computed) on `purchase.order`
  that is True whenever at least one line has a pending vendor proposal.
* Overrides `purchase.order._update_date_planned_for_lines` so POSTs from
  `/my/purchase/<id>/update` write to `date_planned_vendory` instead of
  `date_planned`. `date_planned` is never touched by the vendor.
* Posts a chatter message and raises a warning activity for the purchase
  responsible each time the vendor submits a proposal.
* Adds an "Apply proposed dates" header button that copies
  `date_planned_vendory` into `date_planned` line by line and clears the
  proposal. Only visible when there are pending proposals.
* Renders the proposal column in the order line tree with a warning icon
  in the header (⚠), warning-coloured rows, and auto-hides the column when
  there are no proposals to surface.

Non-goals
---------
* The vendor-facing portal template and email template are untouched — same
  UX for the vendor.
* No controller override — everything hangs off the model method.
    """,
    'depends': ['purchase'],
    'data': [
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
