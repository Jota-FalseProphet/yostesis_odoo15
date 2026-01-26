import logging, traceback, json
from odoo import models

_logger = logging.getLogger(__name__)
SNIFFER_ON = True

def _ensure_sql_table(env):
    env.cr.execute("""
        CREATE TABLE IF NOT EXISTS yostesis_sniffer_log (
            id          BIGSERIAL PRIMARY KEY,
            ts          TIMESTAMPTZ DEFAULT now(),
            origin      TEXT,
            model       TEXT,
            ids         JSONB,
            user_login  TEXT,
            caller      TEXT,
            stack       TEXT,
            vals        JSONB,
            extra       JSONB
        )
    """)

def _sniffer_skip(env):
    ctx = env.context or {}
    return bool(
        ctx.get('from_safe_back2draft')   # tu flujo de "Restaurar albarán"
        or ctx.get('allow_direct_cancel') # cancels internos autorizados
        or ctx.get('skip_sniffer')        # override genérico
    )

def _caller_hint_from_stack():
    stack = traceback.extract_stack(limit=60)
    for fr in reversed(stack):
        path = (fr.filename or "")
        if "/odoo/addons/stock" in path:
            continue
        if "module_sniffer_yostesis" in path:
            continue
        if "/addons/" in path:
            return f"{path}:{fr.lineno} in {fr.name}"
    last = stack[-2]
    return f"{last.filename}:{last.lineno} in {last.name}"

def _log_cancel(env, origin, recs, vals=None, extra=None):
    msg = {
        "origin": origin,
        "model": recs._name,
        "ids": recs.ids,
        "user": env.user.login if env and env.user else None,
        "vals": vals or {},
        "extra": extra or {},
        "caller": _caller_hint_from_stack(),
    }
    stack_txt = "".join(traceback.format_stack(limit=60))

    # 1) A fichero (por si acaso)
    _logger.warning("CANCEL-SNIFFER %s\n%s\nSTACK:\n%s",
                    origin, json.dumps(msg, ensure_ascii=False), stack_txt)

    # 2) A tabla propia (sin depender de ir.logging)
    _ensure_sql_table(env)
    env.cr.execute("""
        INSERT INTO yostesis_sniffer_log(origin, model, ids, user_login, caller, stack, vals, extra)
        VALUES (%s, %s, %s::jsonb, %s, %s, %s, %s::jsonb, %s::jsonb)
    """, (
        origin, recs._name, json.dumps(recs.ids or []),
        msg["user"], msg["caller"], stack_txt,
        json.dumps(msg["vals"]), json.dumps(msg["extra"])
    ))

class StockMove(models.Model):
    _inherit = "stock.move"
    def write(self, vals):
        if SNIFFER_ON and vals.get("state") == "cancel":
            _log_cancel(self.env, "stock.move.write(state=cancel)", self, vals=vals)
        return super().write(vals)
    def _action_cancel(self):
        if SNIFFER_ON and not _sniffer_skip(self.env):
            danger = any(l.qty_done for l in self.move_line_ids)
            _log_cancel(self.env, "stock.move._action_cancel()", self, extra={"has_qty_done": danger})
        return super()._action_cancel()

class StockPicking(models.Model):
    _inherit = "stock.picking"
    def write(self, vals):
        if SNIFFER_ON and vals.get("state") == "cancel":
            _log_cancel(self.env, "stock.picking.write(state=cancel)", self, vals=vals)
        return super().write(vals)
    def action_cancel(self):
        if SNIFFER_ON and not _sniffer_skip(self.env):
            _log_cancel(self.env, "stock.picking.action_cancel()", self)
        return super().action_cancel()
