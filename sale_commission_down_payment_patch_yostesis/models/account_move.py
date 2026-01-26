from odoo import models, api

class AccountMove(models.Model):
    _inherit = "account.move"

    def _recompute_agent_lines(self):
        self.ensure_one()       #solño debe haber un move
        dp_lines = self.invoice_line_ids.filtered(
            lambda l: (
                # en el puto enterprise se marca con display_type="down_payment"
                getattr(l, "display_type", None) == "down_payment"
                # el de la OCA añade booleano is_downpayment en la linea
                or getattr(l, "is_downpayment", False)                    
                or any(getattr(sol, "is_downpayment", False)               
                       for sol in l.sale_line_ids)
            )
        )
        #borro lineas obsoletas
        self.env["account.invoice.line.agent"].search([
            ("object_id", "in", dp_lines.ids)
        ]).unlink()

        #crea las buenas
        for line in dp_lines:
            # intenta usar el helper del modulo de las comisiones
            if hasattr(line, "_get_agents_from_partner"):
                agents_data = line._get_agents_from_partner()
            else:
            #si no existe lo busca en las sale.order ligadas
                agents_data = []
                for sol in line.sale_line_ids:
                    if hasattr(sol, "_get_agents_from_partner"):
                        agents_data += sol._get_agents_from_partner()
                #si aún no hay nada tira de los agentes del partner
                if not agents_data:
                    agents_data = [
                        (ag, ag.commission_id)
                        for ag in line.move_id.partner_id.agent_ids
                    ]

            # ahora sí, crea cada línea de comisiçon
            for agent, commission in agents_data:
                self.env["account.invoice.line.agent"].create({
                    "object_id":     line.id,
                    "invoice_id":    self.id,
                    "agent_id":      agent.id,
                    "commission_id": commission.id,
                })
        
    @api.model_create_multi
    def create(self, vals_list):
        if isinstance(vals_list, dict):
            vals_list = [vals_list]

        moves = super(AccountMove, self).create(vals_list)
        to_process = moves.filtered(lambda m: m.is_sale_document(include_receipts=True))
        for move in to_process:
            move._recompute_agent_lines()
        return moves