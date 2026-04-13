from odoo import SUPERUSER_ID, http
from odoo.exceptions import AccessError, MissingError
from odoo.http import request
from odoo.addons.portal.controllers.portal import CustomerPortal


class PortalPurchaseLabel(CustomerPortal):

    @http.route(
        ['/my/purchase/<int:order_id>/product_label/<int:product_id>'],
        type='http', auth='public', website=True,
    )
    def portal_purchase_product_label(self, order_id, product_id, access_token=None, **kw):
        try:
            order_sudo = self._document_check_access('purchase.order', order_id, access_token=access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        # Verify the product belongs to a line of this order
        product = order_sudo.order_line.product_id.filtered(lambda p: p.id == product_id)
        if not product:
            return request.redirect('/my')

        # Use the same custom Punt Mobles label report as the backend action
        # "Etiquetas Producto" (indaws_stock_customization). The template reads
        # fields like product.measure_data_ids that portal users can't access,
        # so we render with a SUPERUSER environment.
        admin_env = request.env(user=SUPERUSER_ID)
        report = admin_env.ref(
            'indaws_stock_customization.product_product_report_tag_puntmobles_action_wizard'
        )
        pdf, _content_type = report._render_qweb_pdf(res_ids=product.ids)
        pdfhttpheaders = [
            ('Content-Type', 'application/pdf'),
            ('Content-Length', len(pdf)),
            ('Content-Disposition', 'inline; filename="label_%s.pdf"' % (product.default_code or product.id)),
        ]
        return request.make_response(pdf, headers=pdfhttpheaders)
