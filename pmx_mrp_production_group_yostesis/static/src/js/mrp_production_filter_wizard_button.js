console.log("[PMX] JS LOADED: mrp_production_filter_wizard_button.js");
odoo.define("pmx_mrp_production_group_yostesis.mrp_production_filter_wizard_button", function (require) {
    "use strict";

    const ListController = require("web.ListController");
    const core = require("web.core");
    const _t = core._t;

    ListController.include({
        renderButtons() {
            this._super.apply(this, arguments);

            if (!this.$buttons) return;
            if (this.modelName !== "mrp.production") return;
            if (this.viewType !== "list") return;

            if (this.$buttons.find(".o_pmx_open_filter_wizard").length) return;

            const $btn = $('<button type="button" class="btn btn-secondary o_pmx_open_filter_wizard"/>')
                .text(_t("Filtro avanzado"));

            $btn.on("click", async () => {
                $btn.prop("disabled", true);
                try {
                    const active_ids = this.getSelectedIds ? this.getSelectedIds() : [];

                    const state = this.model && this.handle ? this.model.get(this.handle) : {};
                    const ctx = Object.assign({}, (state && state.context) || {});

                    let ptId = ctx.default_picking_type_id || ctx.picking_type_id || ctx.search_default_picking_type_id;

                    if (!ptId) {
                        const dom = (state && state.domain) || [];
                        const candidates = [];
                        for (const t of dom) {
                            if (!Array.isArray(t) || t.length < 3) continue;
                            if (t[0] !== "picking_type_id") continue;
                            if (t[1] === "=") {
                                candidates.push(t[2]);
                            } else if (t[1] === "in" && Array.isArray(t[2]) && t[2].length === 1) {
                                candidates.push(t[2][0]);
                            }
                        }
                        if (candidates.length === 1) {
                            ptId = candidates[0];
                        }
                    }

                    if (ptId && !ctx.default_picking_type_id) {
                        ctx.default_picking_type_id = ptId;
                    }

                    const action = await this._rpc({
                        model: "mrp.production",
                        method: "action_open_filter_wizard",
                        args: [active_ids],
                        kwargs: ptId ? { context: ctx } : undefined,
                    });

                    return this.do_action(action);
                } catch (err) {
                    console.error("PMX: no se pudo abrir el wizard", err);
                    if (this.displayNotification) {
                        this.displayNotification({
                            type: "danger",
                            title: _t("Error"),
                            message: _t("No se pudo abrir el asistente de filtro avanzado."),
                        });
                    } else if (this.do_warn) {
                        this.do_warn(_t("Error"), _t("No se pudo abrir el asistente de filtro avanzado."));
                    }
                } finally {
                    $btn.prop("disabled", false);
                }
            });

            this.$buttons.append($btn);
        },
    });
});

