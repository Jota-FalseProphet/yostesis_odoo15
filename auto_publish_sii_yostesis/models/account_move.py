# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from datetime import timedelta

import logging
import psycopg2

logger = logging.getLogger(__name__)


class AccountMove(models.Model):
    _inherit = 'account.move'

    @api.model
    def check_for_sii(self):

        # Clients
        day_out_invoice = 4
 
        # Providers
        day_in_invoice = 4

        # Days to ignore
        # Saturday Sunday
        ignore_days = [5, 6]

        # Get when to publish
        today = fields.Date.today()
        any_error = False

        # Calculate the real date accounting for weekdays.
        days = day_out_invoice
        date_out_invoice = today
        while days > 0:
            if date_out_invoice.weekday() not in ignore_days:
                days -= 1
            # There is no Do While loop
            if days > 0:
                date_out_invoice = date_out_invoice - timedelta(days=1)
        logger.debug("Max date to send out invoices is: " + str(date_out_invoice))

        companies = self.env['res.company'].search([])  # All companies in DB

        for company in companies:
            if company.sii_enabled and company.sii_auto_upload:

                # ### FIX 1 ▸ soportar ambos nombres de fecha inicio SII
                start_date = getattr(company, 'l10n_es_sii_date_start', False) \
                             or getattr(company, 'sii_date_start', False)

                unsent_sii = [
                    ('state', '=', 'posted'),
                    ('sii_state', '=', 'not_sent'),
                    ('company_id', '=', company.id),
                ]
                # If we should ignore invoices from after starting sii
                if start_date:
                    unsent_sii.append(('invoice_date', '>=', start_date))

                invoices = self.with_company(company).search(unsent_sii)
                filtered_invoices = invoices.filtered(lambda x: x.is_invoice())

                for invoice in filtered_invoices:
                    if invoice.invoice_date:
                        invoice_type = invoice.move_type
                        logger.debug("SII Factura: " + invoice.name + " - Date: " + str(invoice.invoice_date))
                        # Cliente = 'out_invoice'
                        if invoice_type == 'out_invoice':
                            logger.debug("SII Factura: Es cliente")
                            # TODO Eliminar sabados y domingos

                            if invoice.invoice_date <= date_out_invoice:
                                try:
                                    logger.debug("SII Sending factura Cliente")
                                    invoice.send_sii()
                                # ### FIX 2 ▸ manejar colisión de queue.job
                                except psycopg2.errors.SerializationFailure:
                                    self._cr.rollback()
                                    logger.warning("Job concurrency on invoice %s, skipping this run", invoice.name)
                                    continue
                                except Exception as e:
                                    any_error = self.show_sii_error(invoice, e)
                                    continue
                        # Proveedor = 'in_invoice
                        elif invoice_type == 'in_invoice':
                            logger.debug("SII Factura: Es proveedor")
                            # if today.day >= day_in_invoice and (
                            #     (today.year > invoice.invoice_date.year) or
                            #     (today.month > invoice.invoice_date.month)
                            # ):
                            if invoice.invoice_date <= date_out_invoice:
                                try:
                                    logger.debug("SII Sending Factura Proveedor")
                                    invoice.send_sii()
                                except psycopg2.errors.SerializationFailure:
                                    self._cr.rollback()
                                    logger.warning("Job concurrency on invoice %s, skipping this run", invoice.name)
                                    continue
                                except Exception as e:
                                    any_error = self.show_sii_error(invoice, e)
                                    continue

            else:
                logger.info("SII disabled for company " + company.name)

        return not any_error

    @api.model
    def show_sii_error(self, invoice, error):
        error_msg = _("Error sending SII for Invoice {}: {}").format(invoice.name, str(error))
        invoice.activity_schedule(
            activity_type_id = self.env.ref('mail.mail_activity_data_todo').id,
            summary = _("SII Transmission Failed"),
            note = error_msg,
            user_id = invoice.user_id.id or self.env.user.id,
            date_deadline = fields.Date.today()
        )
        logger.error(error_msg)
        return True
