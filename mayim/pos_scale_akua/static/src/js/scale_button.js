odoo.define("pos_scale_akua.ScaleButton", function (require) {
    "use strict";

    const { PosComponent } = require("point_of_sale.PosComponent");
    const ProductScreen = require("point_of_sale.ProductScreen");
    const Registries = require("point_of_sale.Registries");
    const { useListener } = require("web.custom_hooks");

    class ScaleButton extends PosComponent {
        constructor() {
            super(...arguments);
            useListener("click", this.onClick);
        }

        async onClick() {
            try {
                const response = await fetch("http://127.0.0.1:3999/weight", {
                    method: "GET",
                });

                const data = await response.json();

                if (!data.ok || typeof data.kg !== "number") {
                    await this.showPopup("ErrorPopup", {
                        title: this.env._t("Balanza"),
                        body: this.env._t("No hay peso estable"),
                    });
                    return;
                }

                const kg = data.kg;
                const order = this.env.pos.get_order();
                const line = order && order.get_selected_orderline();

                if (!line) {
                    await this.showPopup("ErrorPopup", {
                        title: this.env._t("Balanza"),
                        body: this.env._t("No hay línea seleccionada"),
                    });
                    return;
                }

                line.set_quantity(kg, { doRounding: false });
            } catch (error) {
                await this.showPopup("ErrorPopup", {
                    title: this.env._t("Balanza"),
                    body: this.env._t("No se pudo leer la balanza"),
                });
            }
        }
    }

    ScaleButton.template = "ScaleButton";

    ProductScreen.addControlButton({
        component: ScaleButton,
        condition() {
            return true;
        },
    });

    Registries.Component.add(ScaleButton);

    return ScaleButton;
});
