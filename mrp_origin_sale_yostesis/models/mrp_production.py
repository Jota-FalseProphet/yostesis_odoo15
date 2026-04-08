from odoo import api, fields, models
import logging

_logger = logging.getLogger(__name__)


class MrpProduction(models.Model):
    _inherit = "mrp.production"

    display_origin = fields.Reference(
        string="Origen",
        selection=[
            ('sale.order', 'Pedido de venta'),
            ('purchase.order', 'Pedido de compra'),
            ('mrp.production', 'OF origen'),
        ],
        compute="_compute_display_origin",
        store=True,
        readonly=True,
    )

    origin_product_id = fields.Many2one(
        comodel_name="product.product",
        string="Producto origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    sale_commitment_date = fields.Datetime(
        string="Fecha ent prev PV",
        related="origin_sale.fecha_entrega_prevista",
        store=True,
        readonly=True,
    )

    origin_sale = fields.Many2one(
        comodel_name="sale.order",
        string="Pedido de venta origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    origin_production_id = fields.Many2one(
        comodel_name="mrp.production",
        string="OF origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    sale_line_id = fields.Many2one(
        comodel_name="sale.order.line",
        string="Línea de venta origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    origin_purchase_id = fields.Many2one(
        comodel_name="purchase.order",
        string="Pedido de compra origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    origin_purchase_line_id = fields.Many2one(
        comodel_name="purchase.order.line",
        string="Línea de compra origen",
        compute="_compute_origin_sale",
        store=True,
        readonly=True,
        index=True,
    )

    @api.depends('move_finished_ids.move_dest_ids')
    def _compute_origin_sale(self):
        for record in self:
            sale, product, root_mo, sale_line = record._find_origin_info()
            record.origin_sale = sale
            record.origin_product_id = product
            record.origin_production_id = root_mo
            record.sale_line_id = sale_line

            # Si no se encontró origen de venta, buscar origen de compra
            if not sale and not product:
                po, po_line = record._find_purchase_origin()
                record.origin_purchase_id = po
                record.origin_purchase_line_id = po_line
                if po_line:
                    record.origin_product_id = po_line.product_id
            else:
                record.origin_purchase_id = False
                record.origin_purchase_line_id = False

    @api.depends('origin_sale', 'origin_production_id', 'origin_purchase_id')
    def _compute_display_origin(self):
        for rec in self:
            if rec.origin_sale:
                rec.display_origin = rec.origin_sale
            elif rec.origin_purchase_id:
                rec.display_origin = rec.origin_purchase_id
            elif rec.origin_production_id:
                rec.display_origin = rec.origin_production_id
            else:
                rec.display_origin = False

    def action_confirm(self):
        result = super().action_confirm()
        empty = self.filtered(
            lambda m: m.state != 'cancel' and not m.origin_sale and not m.origin_product_id
        )
        if empty:
            _logger.info(
                'Recomputing origin_sale on confirm for %d MOs: %s',
                len(empty),
                empty.mapped('name'),
            )
            empty._compute_origin_sale()
            empty.flush([
                'origin_sale', 'origin_product_id', 'origin_production_id',
                'sale_line_id', 'origin_purchase_id', 'origin_purchase_line_id',
                'display_origin',
            ])
        return result

    def _find_origin_info(self):
        self.ensure_one()

        result = self._follow_origin_chain()
        if result:
            sale, line = result
            product = line.product_id if line else sale.order_line[:1].product_id
            return sale, product, False, line

        sale_line = self._sale_from_procurement_group(self)
        if sale_line:
            return sale_line.order_id, sale_line.product_id, False, sale_line

        try:
            for src in (self._get_sources() or []):
                if src.origin_sale:
                    return src.origin_sale, src.origin_product_id, src.origin_production_id, src.sale_line_id
                result = src._follow_origin_chain()
                if result:
                    sale, line = result
                    product = line.product_id if line else sale.order_line[:1].product_id
                    return sale, product, False, line
        except Exception:
            pass

        root = self._find_root_production()
        if root:
            if root.origin_sale:
                return root.origin_sale, root.origin_product_id or root.product_id, False, root.sale_line_id
            return False, root.product_id, root, False

        if self.move_raw_ids.move_orig_ids.production_id:
            return False, self.product_id, False, False

        return False, False, False, False

    def _follow_origin_chain(self):
        origin = self.origin
        visited = set()
        # Track product_ids from intermediate MOs to match the correct sale line
        candidate_product_ids = [self.product_id.id]

        for _step in range(15):
            if not origin or origin in visited:
                break
            visited.add(origin)

            so = self.env['sale.order'].search([('name', '=', origin)], limit=1)
            if so:
                # Try matching sale line: last-added MO product first (closest to SO)
                for pid in reversed(candidate_product_ids):
                    line = so.order_line.filtered(
                        lambda l, _pid=pid: l.product_id.id == _pid
                    )
                    if line:
                        return so, line[0]
                return so, so.order_line[:1]

            pick = self.env['stock.picking'].search(
                [('name', '=', origin)], limit=1
            )
            if pick and pick.origin:
                for pid in pick.move_lines.mapped('product_id').ids:
                    if pid not in candidate_product_ids:
                        candidate_product_ids.append(pid)
                origin = pick.origin
                continue

            po = self.env['purchase.order'].search(
                [('name', '=', origin)], limit=1
            )
            if po and po.origin:
                for pid in po.order_line.mapped('product_id').ids:
                    if pid not in candidate_product_ids:
                        candidate_product_ids.append(pid)
                origin = po.origin
                continue

            mo = self.env['mrp.production'].search(
                [('name', '=', origin)], limit=1
            )
            if mo and mo.origin:
                if mo.product_id.id not in candidate_product_ids:
                    candidate_product_ids.append(mo.product_id.id)
                origin = mo.origin
                continue

            break

        return False

    def _find_root_production(self):
        self.ensure_one()
        origin = self.origin
        visited = set()
        root = self.env['mrp.production']

        for _step in range(15):
            if not origin or origin in visited:
                break
            visited.add(origin)

            mo = self.env['mrp.production'].search(
                [('name', '=', origin)], limit=1
            )
            if mo:
                root = mo
                if mo.origin:
                    origin = mo.origin
                    continue
                break

            pick = self.env['stock.picking'].search(
                [('name', '=', origin)], limit=1
            )
            if pick and pick.origin:
                origin = pick.origin
                continue

            po = self.env['purchase.order'].search(
                [('name', '=', origin)], limit=1
            )
            if po and po.origin:
                origin = po.origin
                continue

            break

        return root

    def _sale_from_procurement_group(self, mo):
        pg = mo.procurement_group_id
        if not pg:
            return False
        dest_groups = pg.mrp_production_ids.move_dest_ids.group_id
        sale_lines = dest_groups.stock_move_ids.mapped('sale_line_id')
        if not sale_lines:
            return False
        match = sale_lines.filtered(
            lambda l: l.product_id.id == self.product_id.id
        )
        return match[0] if match else sale_lines[0]

    def _find_purchase_origin(self):
        """Recorre el grafo de moves hacia adelante desde los finished moves
        para encontrar la línea de compra que originó esta OF (subcontratación).

        Cadena típica:
          OF finished_move → OUT-SUB move → SBC MO raw_move
          → SBC MO finished_move → Receipt move (tiene purchase_line_id)
        """
        self.ensure_one()
        visited = set()
        moves = self.move_finished_ids

        for _depth in range(10):
            next_moves = self.env['stock.move']
            for m in moves:
                if m.id in visited:
                    continue
                visited.add(m.id)
                if m.purchase_line_id:
                    return m.purchase_line_id.order_id, m.purchase_line_id
                next_moves |= m.move_dest_ids
                # Si el move alimenta un MO como materia prima, saltar a sus finished moves
                if m.raw_material_production_id:
                    next_moves |= m.raw_material_production_id.move_finished_ids
            new_ids = set(next_moves.ids) - visited
            if not new_ids:
                break
            moves = self.env['stock.move'].browse(list(new_ids))

        return False, False
