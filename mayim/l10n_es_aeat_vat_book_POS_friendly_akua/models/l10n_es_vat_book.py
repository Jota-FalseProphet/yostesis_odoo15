from odoo import _, models


class L10nEsVatBook(models.Model):
    _inherit = "l10n.es.vat.book"

    def _check_exceptions(self, line_vals):
        move = self.env["account.move"].browse(
            line_vals.get("move_id")
        ) if line_vals.get("move_id") else self.env["account.move"]

        if (
            not line_vals.get("partner_id")
            and move
            and move.journal_id
            and getattr(move.journal_id, "vat_book_pos_anonymous", False)
        ):
            return

        rp_model = self.env["res.partner"]

        if not line_vals["partner_id"]:
            line_vals["exception_text"] = _("Without Partner")
        elif not line_vals["vat_number"]:
            partner = rp_model.browse(line_vals["partner_id"])
            country_code, identifier_type, vat_number = partner._parse_aeat_vat_info()
            req_vat_identif_types = [
                s_opt[0]
                for s_opt in rp_model._fields["aeat_identification_type"].selection
            ] + [""]
            if (
                identifier_type in req_vat_identif_types
                and line_vals["partner_id"] not in self.get_pos_partner_ids()
            ):
                line_vals["exception_text"] = _("Without VAT")
