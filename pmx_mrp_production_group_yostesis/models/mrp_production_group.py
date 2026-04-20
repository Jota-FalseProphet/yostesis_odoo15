from collections import defaultdict
from odoo import api, fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = "stock.picking"
    production_group_id = fields.Many2one("mrp.production.group", index=True)


class MrpProductionGroup(models.Model):
    _name = "mrp.production.group"
    _description = "Agrupación de Órdenes de Fabricación"
    _order = "group_date desc, id desc"

    name = fields.Char(required=True, copy=False, readonly=True, default=lambda self: _("New"))
    group_date = fields.Date(required=True, default=fields.Date.context_today)
    start_date = fields.Date()
    company_id = fields.Many2one("res.company", required=True, default=lambda self: self.env.company)
    production_ids = fields.One2many("mrp.production", "group_id", string="Órdenes de fabricación")
    production_count = fields.Integer(compute="_compute_production_count")
    picking_type_id = fields.Many2one("stock.picking.type", string="Tipo de operación")
    picking_id = fields.Many2one("stock.picking", string="Albarán de preparación", copy=False, readonly=True)
    note = fields.Html(string="Notas")

    picking_all_ids = fields.Many2many(
        "stock.picking",
        compute="_compute_picking_all",
        string="Albaranes",
        readonly=True,
    )
    picking_all_count = fields.Integer(
        compute="_compute_picking_all",
        string="Nº albaranes",
        readonly=True,
    )

    component_detail_ids = fields.One2many(
        "mrp.production.group.component.detail",
        "group_id",
        string="Componentes detallados",
        copy=False,
    )

    component_ids = fields.One2many(
        "mrp.production.group.component",
        "group_id",
        string="Componentes",
        copy=False,
    )

    picking_ids = fields.One2many(
        "stock.picking",
        "production_group_id",
        string="Albaranes relacionados",
        readonly=True,
    )
    state = fields.Selection(
        [("draft", "Borrador"),
         ("picking_generated", "Albarán generado"),
         ("partial_done", "Parcialmente hecho"),
         ("done", "Hecho")
        ],
        compute="_compute_state",
        store=True,
        readonly=True,
    )
    production_m2m_ids = fields.Many2many(
        comodel_name="mrp.production",
        string="Órdenes de fabricación",
        compute="_compute_production_m2m_ids",
        inverse="_inverse_production_m2m_ids",
        readonly=False,
    )
    pmx_show_create_picking_button = fields.Boolean(
        compute="_compute_pmx_show_create_picking_button",
        string="Mostrar botón crear albarán",
    )

    @api.depends(
        "state",
        "component_ids.qty_total",
        "picking_id",
        "picking_id.move_ids_without_package.product_uom_qty",
        "picking_id.move_ids_without_package.state",
        "picking_ids",
        "picking_ids.move_ids_without_package.product_uom_qty",
        "picking_ids.move_ids_without_package.state",
    )
    def _compute_pmx_show_create_picking_button(self):
        for group in self:
            if group.state == "draft":
                group.pmx_show_create_picking_button = True
                continue

            # Collect all related pickings, excluding cancelled ones
            # (done pickings count: components are not removed when a picking is validated)
            all_pickings = group.picking_ids
            if group.picking_id:
                all_pickings = all_pickings | group.picking_id
            relevant_pickings = all_pickings.filtered(lambda p: p.state != "cancel")

            # Sum demanded qty per product across relevant picking moves (non-cancelled moves)
            picked_qty = defaultdict(float)
            for picking in relevant_pickings:
                for move in picking.move_ids_without_package.filtered(lambda m: m.state != "cancel"):
                    if move.product_id:
                        picked_qty[move.product_id.id] += move.product_uom_qty

            # Show button if any component has more qty than what's covered by pickings
            show = any(
                comp.qty_total > picked_qty.get(comp.product_id.id, 0.0)
                for comp in group.component_ids
                if comp.product_id
            )
            group.pmx_show_create_picking_button = show

    def _collect_backorder_chain(self, root_picking):
        Picking = self.env['stock.picking'].sudo()
        seen = Picking.browse()
        to_process = root_picking
        while to_process:
            seen |= to_process
            to_process = to_process.mapped('backorder_ids') - seen
        return seen

    @api.depends("picking_id", "picking_ids", "picking_ids.backorder_ids")
    def _compute_picking_all(self):
        Picking = self.env["stock.picking"].sudo()
        for group in self:
            pickings = Picking.browse()

            pickings |= Picking.search([("production_group_id", "=", group.id)])
            pickings |= group.picking_ids.sudo()

            if group.picking_id:
                seen = group._collect_backorder_chain(group.picking_id)
                pickings |= seen

            group.picking_all_ids = pickings
            group.picking_all_count = len(pickings)

    @api.depends(
        "picking_ids",
        "picking_ids.state",
        "picking_ids.backorder_ids",
        "picking_ids.backorder_ids.state",
        "picking_id",
        "picking_id.state",
        "picking_id.backorder_ids",
        "picking_id.backorder_ids.state",
    )
    def _compute_state(self):
        for group in self:
            pickings = group.picking_ids.sudo()

            if group.picking_id:
                seen = group._collect_backorder_chain(group.picking_id.sudo())
                pickings |= seen

            if not pickings:
                group.state = "draft"
                continue

            relevant = pickings.filtered(lambda p: p.state != "cancel")
            if not relevant:
                group.state = "picking_generated"
                continue

            done = relevant.filtered(lambda p: p.state == "done")
            if len(done) == len(relevant):
                group.state = "done"
            elif done:
                group.state = "partial_done"
            else:
                group.state = "picking_generated"


    def action_open_group_pickings(self):
        self.ensure_one()
        pickings = self.picking_all_ids
        if not pickings:
            raise UserError(_("No hay albaranes relacionados con esta agrupación."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Albaranes"),
            "res_model": "stock.picking",
            "view_mode": "tree,form",
            "domain": [("id", "in", pickings.ids)],
            "context": {
                "search_default_group_by_picking_type_id": 0,
                "default_production_group_id": self.id,
            },
            "target": "current",
        }
    
    def _detail_lines_filtered(self):
        self.ensure_one()
        lines = self.component_detail_ids
        if "excluded" in lines._fields:
            lines = lines.filtered(lambda l: not l.excluded)
        lines = lines.filtered(lambda l: l.product_id and l.product_uom_id and (l.qty or 0.0) > 0.0)
        return lines

    def _qty_field_agg(self):
        Agg = self.env["mrp.production.group.component"].sudo()
        if "qty_total" in Agg._fields:
            return "qty_total"
        if "qty" in Agg._fields:
            return "qty"
        raise UserError(_("El modelo de componentes agregados no tiene campo de cantidad (qty_total/qty)."))

    def _after_detail_change(self):
        self._rebuild_aggregates_from_details()
        self._sync_preparation_picking_from_details()

    def _rebuild_aggregates_from_details(self):
        Agg = self.env["mrp.production.group.component"].sudo()

        qty_field = self._qty_field_agg()

        for group in self:
            group.component_ids.sudo().unlink()

            pt = group.picking_type_id
            default_src_id = pt.default_location_src_id.id if pt and pt.default_location_src_id else False

            totals = defaultdict(float)

            lines = group._detail_lines_filtered()

            for l in lines:
                loc_id = l.location_id.id if l.location_id else default_src_id
                totals[(l.product_id.id, l.product_uom_id.id, loc_id)] += l.qty

            vals_list = []
            for (product_id, uom_id, location_id), qty in totals.items():
                vals = {
                    "group_id": group.id,
                    "product_id": product_id,
                    "product_uom_id": uom_id,
                    "location_id": location_id or False,
                }
                vals[qty_field] = qty
                vals_list.append(vals)

            if vals_list:
                Agg.create(vals_list)

    def action_open_picking(self):
        self.ensure_one()
        if not self.picking_id:
            raise UserError(_("No hay albarán asociado."))
        return {
            "type": "ir.actions.act_window",
            "name": _("Albarán de preparación"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": self.picking_id.id,
            "target": "current",
        }

    def _prefill_detailed_operations(self, picking):
        picking.ensure_one()
        if picking.move_line_ids.filtered(lambda ml: (ml.qty_done or 0.0) > 0.0):
            raise UserError(_("El albarán ya tiene cantidades hechas en operaciones detalladas (qty_done)."))

        picking.move_line_ids_without_package.unlink()

        MoveLine = self.env["stock.move.line"].sudo()

        for move in picking.move_ids_without_package.filtered(lambda m: m.state not in ("done", "cancel")):
            qty = move.product_uom_qty or 0.0
            if qty <= 0.0:
                continue

            vals = {
                "picking_id": picking.id,
                "move_id": move.id,
                "company_id": picking.company_id.id,
                "product_id": move.product_id.id,
                "product_uom_id": move.product_uom.id,
                "location_id": move.location_id.id,
                "location_dest_id": move.location_dest_id.id,
            }

            vals['qty_done'] = qty if move.product_id.tracking == 'none' else 0.0

            MoveLine.create(vals)

    def action_create_preparation_picking(self):
        self.ensure_one()

        if not self.picking_type_id:
            raise UserError(_("Debes seleccionar un Tipo de operación."))

        if self.picking_type_id.company_id and self.picking_type_id.company_id != self.company_id:
            raise UserError(_("El Tipo de operación no pertenece a la misma compañía que la agrupación."))

        pt = self.picking_type_id
        if not pt.default_location_src_id or not pt.default_location_dest_id:
            raise UserError(_("El Tipo de operación no tiene ubicaciones origen/destino configuradas."))

        mos = self.production_ids.filtered(lambda m: m.state not in ("cancel", "done"))
        if not mos:
            raise UserError(_("La agrupación no tiene OF válidas."))
        if any(m.state == "draft" for m in mos):
            raise UserError(_("Hay OF en borrador. Confírmalas antes de generar el albarán."))

        lines = self._detail_lines_filtered()
        if not lines:
            raise UserError(_("No hay componentes detallados para preparar (o están todos excluidos)."))

        totals = defaultdict(float)
        for l in lines:
            src_loc_id = l.location_id.id if l.location_id else pt.default_location_src_id.id
            totals[(l.product_id.id, l.product_uom_id.id, src_loc_id)] += l.qty

        if not totals:
            raise UserError(_("No se han encontrado componentes para totalizar."))

        SaleOrder = self.env["sale.order"]
        origins = {mo.origin for mo in mos if mo.origin}
        partner_id = False

        if origins:
            sos = SaleOrder.search([("name", "in", list(origins))])
            partners = {so.partner_id.id for so in sos if so.partner_id}
            partner_id = next(iter(partners)) if len(partners) == 1 else self.company_id.partner_id.id if self.company_id.partner_id else False


        if not partner_id:
            partner_id = self.company_id.partner_id.id if self.company_id.partner_id else False
            if not partner_id:
                raise UserError(_("No se ha podido determinar un contacto para el albarán. Revisa la compañía o el origen de las OF."))

        # Validate and prepare the existing main picking if still active
        if self.picking_id and self.picking_id.state not in ("cancel", "done"):
            existing = self.picking_id
            if existing.company_id != self.company_id:
                raise UserError(_("El albarán asociado pertenece a otra compañía."))
            if existing.picking_type_id != pt:
                raise UserError(_("El albarán asociado tiene un Tipo de operación distinto. Cancélalo y vuelve a generarlo."))
            if existing.state == "assigned":
                existing.action_unreserve()

        # Compute quantities already covered by non-cancelled pickings
        covered = defaultdict(float)
        all_existing = self.picking_ids
        if self.picking_id:
            all_existing = all_existing | self.picking_id
        for p in all_existing.filtered(lambda p: p.state != "cancel"):
            for m in p.move_ids_without_package.filtered(lambda m: m.state != "cancel"):
                if m.product_id:
                    covered[m.product_id.id] += m.product_uom_qty

        # Compute missing quantities: total needed minus what's already in pickings.
        # Iterate in a stable order so coverage is applied consistently when a product
        # appears in multiple (product, uom, location) combos.
        covered_used = defaultdict(float)
        missing = {}
        for (product_id, uom_id, src_loc_id), qty in sorted(totals.items()):
            available = max(0.0, covered[product_id] - covered_used[product_id])
            if available >= qty:
                covered_used[product_id] += qty
            elif available > 0:
                covered_used[product_id] += available
                missing[(product_id, uom_id, src_loc_id)] = qty - available
            else:
                missing[(product_id, uom_id, src_loc_id)] = qty

        if not missing:
            raise UserError(_("Todos los componentes ya están cubiertos por los albaranes existentes."))

        # Always create a new picking with only the missing items.
        # Existing pickings are never modified.
        picking = self.env["stock.picking"].create({
            "picking_type_id": pt.id,
            "company_id": self.company_id.id,
            "origin": self.name,
            "production_group_id": self.id,
            "partner_id": partner_id,
            "location_id": pt.default_location_src_id.id,
            "location_dest_id": pt.default_location_dest_id.id,
            "note": self.note or False,
        })

        Move = self.env["stock.move"].sudo()
        Product = self.env["product.product"].sudo()

        for (product_id, uom_id, src_loc_id), qty in missing.items():
            Move.create({
                "name": Product.browse(product_id).display_name,
                "picking_id": picking.id,
                "product_id": product_id,
                "product_uom": uom_id,
                "product_uom_qty": qty,
                "location_id": src_loc_id,
                "location_dest_id": picking.location_dest_id.id,
                "company_id": self.company_id.id,
            })

        if picking.state not in ("done", "cancel"):
            picking.action_confirm()
            self._prefill_detailed_operations(picking)

        # Only promote to picking_id if there is no active main picking yet
        if not self.picking_id or self.picking_id.state == "cancel":
            self.picking_id = picking.id

        return {
            "type": "ir.actions.act_window",
            "name": _("Albarán de preparación"),
            "res_model": "stock.picking",
            "view_mode": "form",
            "res_id": picking.id,
            "target": "current",
        }

    def _sync_preparation_picking_from_details(self):
        for group in self:
            picking = group.picking_id
            if not picking or picking.state in ("done", "cancel"):
                continue
            if picking.move_line_ids.filtered(lambda ml: (ml.qty_done or 0.0) > 0.0):
                continue

            if picking.state == "assigned":
                picking.action_unreserve()

            picking.move_ids_without_package.filtered(lambda m: m.state not in ("done", "cancel")).unlink()

            pt = group.picking_type_id
            src_default = pt.default_location_src_id if pt and pt.default_location_src_id else picking.location_id
            dst_default = pt.default_location_dest_id if pt and pt.default_location_dest_id else picking.location_dest_id
            picking.write({"note": group.note or False})

            totals = defaultdict(float)
            lines = group._detail_lines_filtered()
            for l in lines:
                src = l.location_id or src_default
                totals[(l.product_id.id, l.product_uom_id.id, src.id if src else False)] += l.qty

            Move = self.env["stock.move"].sudo()
            Product = self.env["product.product"].sudo()

            for (product_id, uom_id, src_id), qty in totals.items():
                Move.create({
                    "name": Product.browse(product_id).display_name,
                    "picking_id": picking.id,
                    "product_id": product_id,
                    "product_uom": uom_id,
                    "product_uom_qty": qty,
                    "location_id": src_id or (src_default.id if src_default else False),
                    "location_dest_id": dst_default.id if dst_default else False,
                    "company_id": group.company_id.id,
                })

            picking.action_confirm()
            group._prefill_detailed_operations(picking)

    def action_rebuild_components(self):
        for group in self:
            group._rebuild_components()
        return True

    def _rebuild_components(self):
        self.ensure_one()

        mos = self.production_ids.filtered(lambda m: m.state not in ("cancel", "done"))
        Detail = self.env["mrp.production.group.component.detail"].sudo()

        # Limpieza atómica (evita recalcular a mitad si Detail tiene hooks)
        self.component_detail_ids.with_context(skip_group_after_change=True).sudo().unlink()
        self.component_ids.sudo().unlink()

        if not mos:
            if self.picking_id and self.picking_id.state not in ("done", "cancel"):
                self._after_detail_change()
            return

        # Reconstruye desde la misma lógica central (moves si existen; si no, engine estándar)
        detail_vals = []
        for mo in mos:
            detail_vals += self._detail_vals_from_mo(mo)

        if detail_vals:
            CHUNK = 1000
            for i in range(0, len(detail_vals), CHUNK):
                Detail.with_context(skip_group_after_change=True).create(detail_vals[i:i + CHUNK])

        # Un único recalculo final
        self._after_detail_change()

    @api.depends("production_ids")
    def _compute_production_count(self):
        for rec in self:
            rec.production_count = len(rec.production_ids)

    @api.model
    def create(self, vals):
        if not vals.get("picking_type_id"):
            ctx = self.env.context or {}

            pt_id = ctx.get("default_picking_type_id") or ctx.get("pmx_mrp_group_target_picking_type_id")
            if pt_id:
                vals["picking_type_id"] = pt_id
            else:
                stp1 = False
                stp1_id = ctx.get("pmx_mrp_group_stp1_id")
                if stp1_id:
                    stp1 = self.env["stock.picking.type"].browse(stp1_id).exists()

                if not stp1:
                    mo_ids = []
                    if ctx.get("preselect_model") == "mrp.production":
                        mo_ids = ctx.get("preselect_ids") or []
                    if not mo_ids and ctx.get("active_model") == "mrp.production":
                        mo_ids = ctx.get("active_ids") or []

                    if mo_ids:
                        mos = self.env["mrp.production"].browse(mo_ids).exists()
                        pts = mos.mapped("picking_type_id").exists()
                        if len(pts) == 1:
                            stp1 = pts

                if stp1:
                    stp3 = stp1
                    if stp1.code == "mrp_operation":
                        stp3 = stp1.pmx_mrp_group_target_picking_type_id
                        if not stp3:
                            raise UserError(_(
                                "El Tipo de operación '%s' no tiene configurado "
                                "'Tipo operación para la Agrupación OFs' (STP3)."
                            ) % stp1.display_name)
                    vals["picking_type_id"] = stp3.id

        if vals.get("name", _("New")) == _("New"):
            vals["name"] = self.env["ir.sequence"].next_by_code("mrp.production.group") or _("New")

        rec = super().create(vals)
        rec._set_start_date_if_empty()
        return rec

    def write(self, vals):
        res = super().write(vals)
        self._set_start_date_if_empty()

        if "picking_type_id" in vals:
            for rec in self:
                rec._rebuild_aggregates_from_details()
                rec._sync_preparation_picking_from_details()
        if "note" in vals:
            for rec in self:
                pickings = (rec.picking_id | rec.picking_ids).filtered(lambda p: p.state not in ("done", "cancel"))
                if pickings:
                    pickings.write({"note": rec.note or False})
        return res

    def _set_start_date_if_empty(self):
        for rec in self:
            if rec.start_date:
                continue
            dates = rec.production_ids.mapped("date_planned_start")
            dates = [d for d in dates if d]
            if dates:
                rec.start_date = min(dates).date()

    def action_open_add_mos_wizard(self):
        self.ensure_one()
        ctx = {"default_group_id": self.id}
        if self.picking_type_id:
            ctx["default_picking_type_id"] = self.picking_type_id.id

        return {
            "type": "ir.actions.act_window",
            "name": _("Añadir OF"),
            "res_model": "mrp.production.group.add.wizard",
            "view_mode": "form",
            "target": "new",
            "context": ctx,
        }

    def _recompute_start_date(self):
        for rec in self:
            dates = [d for d in rec.production_ids.mapped("date_planned_start") if d]
            rec.start_date = min(dates).date() if dates else False

    def _detail_vals_from_mo(self, mo):
        self.ensure_one()

        pt = self.picking_type_id or mo.picking_type_id

        src_loc = pt.default_location_src_id if pt and pt.default_location_src_id else False
        src_loc_id = src_loc.id if src_loc else False

        Detail = self.env["mrp.production.group.component.detail"].sudo()
        vals_list = []

        unit_uom = self.env.ref("uom.product_uom_unit", raise_if_not_found=False)
        unit_category_id = unit_uom.category_id.id if unit_uom else False

        def is_almost_int(x, tol=1e-6):
            return abs(x - round(x)) <= tol

        moves = mo.move_raw_ids.filtered(lambda x: x.state != "cancel")
        has_move_id = "move_id" in Detail._fields
        if moves:
            for mv in moves:
                if not mv.product_id or not mv.product_uom:
                    continue

                qty = mv.product_uom_qty or 0.0
                if qty <= 0:
                    continue

                loc_id = src_loc_id or (mv.location_id.id if mv.location_id else False)

                vals = {
                    "group_id": self.id,
                    "production_id": mo.id,
                    "product_id": mv.product_id.id,
                    "product_uom_id": mv.product_uom.id,
                    "qty": qty,
                    "location_id": loc_id or False,
                    "excluded": False,
                }
                if has_move_id:
                    vals["move_id"] = mv.id

                vals_list.append(vals)

            return vals_list

        return vals_list

        # Fallback desactivado: si la OF no tiene move_raw_ids, el grupo
        # no debe inventarse componentes desde la lista de materiales jeje
        # Bom = self.env["mrp.bom"]
        # bom = mo.bom_id
        # if not bom:
        #     bom = Bom.search([
        #         ("type", "=", "normal"),
        #         ("product_tmpl_id", "=", mo.product_id.product_tmpl_id.id),
        #         ("company_id", "in", [False, mo.company_id.id]),
        #         "|",
        #         ("product_id", "=", False),
        #         ("product_id", "=", mo.product_id.id),
        #     ], order="product_id desc, sequence, id", limit=1)
        #
        # if not bom:
        #     return []
        #
        # bom_qty = bom.product_qty or 1.0
        # mo_qty_in_bom_uom = mo.product_uom_id._compute_quantity(mo.product_qty, bom.product_uom_id)
        # factor = mo_qty_in_bom_uom / bom_qty
        #
        # loc_id = src_loc_id or False
        #
        # for line in bom.bom_line_ids:
        #     if getattr(line, "display_type", False):
        #         continue
        #     if not line.product_id or not line.product_uom_id:
        #         continue
        #     qty = (line.product_qty or 0.0) * factor
        #     if qty <= 0:
        #         continue
        #
        #     uom = line.product_uom_id
        #
        #     if unit_category_id and uom.category_id.id == unit_category_id and is_almost_int(qty):
        #         n = int(round(qty))
        #         if n > 0:
        #             for _i in range(n):
        #                 vals = {
        #                     "group_id": self.id,
        #                     "production_id": mo.id,
        #                     "product_id": line.product_id.id,
        #                     "product_uom_id": uom.id,
        #                     "qty": 1.0,
        #                     "location_id": loc_id or False,
        #                     "excluded": False,
        #                 }
        #                 if has_move_id:
        #                     vals["move_id"] = False
        #                 vals_list.append(vals)
        #     else:
        #         vals = {
        #             "group_id": self.id,
        #             "production_id": mo.id,
        #             "product_id": line.product_id.id,
        #             "product_uom_id": uom.id,
        #             "qty": qty,
        #             "location_id": loc_id or False,
        #             "excluded": False,
        #         }
        #         if has_move_id:
        #             vals["move_id"] = False
        #         vals_list.append(vals)
        # return vals_list

    def _ensure_details_for_mos(self, mos):
        Detail = self.env["mrp.production.group.component.detail"].sudo()

        for group in self:
            group_mos = mos.filtered(lambda m: m.group_id == group and m.state not in ("cancel", "done"))
            if not group_mos:
                continue

            to_create = []
            existing_mo_ids = set(
                Detail.search([("group_id", "=", group.id), ("production_id", "in", group_mos.ids)]).mapped("production_id").ids
            )

            for mo in group_mos:
                if mo.id in existing_mo_ids:
                    continue
                to_create += group._detail_vals_from_mo(mo)

            if to_create:
                Detail.with_context(skip_group_after_change=True).create(to_create)

            group._recompute_start_date()
            group._after_detail_change()

    def _remove_details_for_mos(self, mos):
        Detail = self.env["mrp.production.group.component.detail"].sudo()

        for group in self:
            group_mos = mos.filtered(lambda m: (m.group_id == group) or (not m.group_id))
            mo_ids = group_mos.ids or mos.ids
            if not mo_ids:
                continue

            Detail.with_context(skip_group_after_change=True).search([
                ("group_id", "=", group.id),
                ("production_id", "in", mo_ids),
            ]).unlink()

            group._recompute_start_date()
            group._after_detail_change()

    @api.depends("production_ids")
    def _compute_production_m2m_ids(self):
        for group in self:
            group.production_m2m_ids = group.production_ids

    def _inverse_production_m2m_ids(self):
        """
        Cuando el usuario añade/quita OFs en production_m2m_ids:
        - Añadidas => group_id = this group
        - Quitadas => group_id = False (solo si estaban en este grupo)
        """
        for group in self:
            desired = group.production_m2m_ids
            current = group.production_ids

            to_add = (desired - current).exists()
            to_remove = (current - desired).exists()

            # Si quieres evitar que "robe" OFs de otros grupos, mejor restringir por domain en la vista.
            # Aun así, por seguridad, impedimos quitar/poner si pertenecen a otro grupo distinto.
            stolen = to_add.filtered(lambda m: m.group_id and m.group_id != group)
            if stolen:
                raise UserError(_(
                    "No puedes añadir OFs que ya están en otra agrupación (%s)."
                ) % ", ".join(stolen.mapped("group_id.display_name")))

            if to_add:
                to_add.write({"group_id": group.id})
                if hasattr(group, "_ensure_details_for_mos"):
                    group._ensure_details_for_mos(to_add)

            if to_remove:
                # Solo desasignamos las que estaban en ESTE grupo
                to_unlink = to_remove.filtered(lambda m: m.group_id == group)
                if to_unlink:
                    to_unlink.write({"group_id": False})
                    if hasattr(group, "_remove_details_for_mos"):
                        group._remove_details_for_mos(to_unlink)

            if hasattr(group, "_recompute_start_date"):
                group._recompute_start_date()
            elif hasattr(group, "_set_start_date_if_empty"):
                group._set_start_date_if_empty()

    def _get_all_pickings(self):
        self.ensure_one()
        pickings = self.picking_all_ids.sudo()
        return pickings

    def action_delete_group(self):
        for group in self:
            pickings = group._get_all_pickings()

            done_pickings = pickings.filtered(lambda p: p.state == "done")
            if done_pickings:
                raise UserError(_(
                    "No puedes eliminar la agrupación '%s' porque tiene albaranes validados: %s"
                ) % (group.display_name, ", ".join(done_pickings.mapped("name"))))

            to_cancel = pickings.filtered(lambda p: p.state not in ("cancel", "done"))
            if to_cancel:
                mls = to_cancel.mapped("move_line_ids")
                if mls:
                    mls.write({"qty_done": 0.0})

                moves = to_cancel.mapped("move_ids_without_package")
                if moves and "quantity_done" in moves._fields:
                    moves.write({"quantity_done": 0.0})

                to_cancel.action_cancel()

            group.with_context(pmx_group_delete_force=True).unlink()

        return {
            "type": "ir.actions.act_window",
            "name": _("Agrupaciones de OF"),
            "res_model": "mrp.production.group",
            "view_mode": "tree,form",
            "target": "current",
        }

    def unlink(self):
        for group in self:
            pickings = group._get_all_pickings()

            done_pickings = pickings.filtered(lambda p: p.state == "done")
            if done_pickings:
                raise UserError(_(
                    "No puedes eliminar la agrupación '%s' porque tiene albaranes validados: %s"
                ) % (group.display_name, ", ".join(done_pickings.mapped("name"))))

            to_cancel = pickings.filtered(lambda p: p.state not in ("cancel", "done"))
            if to_cancel and not self.env.context.get("pmx_group_delete_force"):
                raise UserError(_(
                    "Esta agrupación tiene albaranes sin cancelar: %s\n"
                    "No se permite borrar desde la papelera.\n"
                    "Abre la agrupación y usa el botón rojo 'Eliminar agrupación' (cancela albaranes y borra)."
                ) % (", ".join(to_cancel.mapped("name"))))

        return super().unlink()
