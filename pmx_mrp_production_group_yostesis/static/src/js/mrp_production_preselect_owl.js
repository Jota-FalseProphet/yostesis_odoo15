odoo.define("pmx_mrp_production_group_yostesis.preselect_list_rows", function (require) {
    "use strict";

    const ListRenderer = require("web.ListRenderer");

    function _getCtx(renderer) {
        return (renderer.state && renderer.state.context) || {};
    }

    ListRenderer.include({
        _renderView() {
            const prom = this._super.apply(this, arguments);

            return Promise.resolve(prom).then(() => {
                try {
                    if (!this.state || this.state.model !== "mrp.production") return;
                    if (this._pmx_preselect_done) return;

                    const ctx = _getCtx(this);
                    const ids = (ctx.preselect_ids || []).map(Number);
                    const model = ctx.preselect_model;

                    console.log(
                        "[PMX] renderer preselect model=",
                        this.state.model,
                        "ctx.model=",
                        model,
                        "len=",
                        ids.length
                    );

                    if (!ids.length) return;
                    if (model !== this.state.model) return;

                    const target = new Set(ids);
                    const rows = (this.state && this.state.data) || [];

                    // Espera a que el DOM esté pintado y handlers listos
                    setTimeout(() => {
                        let hits = 0;
                        let clicked = 0;

                        const clickedCbs = [];

                        for (const r of rows) {
                            if (!target.has(r.res_id)) continue;

                            const $tr = this.$el.find("tr.o_data_row[data-id='" + r.id + "']");
                            if (!$tr.length) continue;

                            hits++;

                            const $cb = $tr.find(".o_list_record_selector input[type='checkbox']");
                            if (!$cb.length) continue;

                            if ($cb.prop("checked")) continue;

                            $cb[0].click();
                            clicked++;
                            clickedCbs.push($cb[0]);
                        }

                        console.log("[PMX] preselect hits=", hits, "clicked=", clicked);

                        if (hits > 0) {
                            this._pmx_preselect_done = true;
                            delete ctx.preselect_ids;
                            delete ctx.preselect_model;

                            // Fuerza refresco del control panel (engranaje) sin cambiar el estado final
                            // OFF/ON sobre 1 fila para disparar “selection changed”
                            if (clickedCbs.length) {
                                requestAnimationFrame(() => {
                                    clickedCbs[0].click(); // off
                                    requestAnimationFrame(() => {
                                        clickedCbs[0].click(); // on (estado final: todo marcado)
                                    });
                                });
                            }

                            if (typeof this._renderSelection === "function") {
                                this._renderSelection();
                            }
                        }
                    }, 0);
                } catch (e) {
                    console.error("[PMX] renderer preselect failed", e);
                }
            });
        },
    });
});
