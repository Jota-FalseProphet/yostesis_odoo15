from odoo import api, models


class AccountReconciliationWidget(models.AbstractModel):
    _inherit = "account.reconciliation.widget"

    @api.model
    def _get_query_reconciliation_widget_suspense_lines(self, statement_line, domain=None):
        if domain is None:
            domain = []
        suspense_account = statement_line.journal_id.suspense_account_id
        if not suspense_account:
            return "", []
        domain = domain + [
            ("display_type", "not in", ("line_section", "line_note")),
            ("parent_state", "=", "posted"),
            ("reconciled", "=", False),
            ("balance", "!=", 0.0),
            ("company_id", "=", statement_line.company_id.id),
            ("account_id", "=", suspense_account.id),
            ("move_id", "!=", statement_line.move_id.id),
        ]
        AML = self.env["account.move.line"]
        AML.check_access_rights("read")
        query_obj = AML._where_calc(domain)
        AML._apply_ir_rules(query_obj)
        tables, where_clause, where_params = query_obj.get_sql()
        query = """
            SELECT %s
            FROM %s
            WHERE %s
        """ % (
            self._get_query_select_clause(),
            tables,
            where_clause,
        )
        return query, where_params

    @api.model
    def _get_query_reconciliation_widget_customer_vendor_matching_lines(self, statement_line, domain=None):
        if domain is None:
            domain = []
        query_1, params_1 = self._get_query_reconciliation_widget_liquidity_lines(
            statement_line, domain=domain,
        )
        query_2, params_2 = self._get_query_reconciliation_widget_receivable_payable_lines(
            statement_line, domain=domain,
        )
        query_3, params_3 = self._get_query_reconciliation_widget_suspense_lines(
            statement_line, domain=domain,
        )
        unions = [query_1, query_2]
        all_params = params_1 + params_2
        if query_3:
            unions.append(query_3)
            all_params += params_3
        query = """
            SELECT *, count(*) OVER() AS full_count
            FROM (
                %s
            ) AS account_move_line
        """ % "\n\n                UNION ALL\n\n                ".join(unions)
        return query, all_params
