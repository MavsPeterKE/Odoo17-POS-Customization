/** @odoo-module */

import { registry } from "@web/core/registry";
import { ClosePosPopup } from "@point_of_sale/app/navbar/closing_popup/closing_popup";
import { ConfirmPopup } from "@point_of_sale/app/utils/confirm_popup/confirm_popup";
import { useService } from "@web/core/utils/hooks";
import { _t } from "@web/core/l10n/translation";
import { patch } from "@web/core/utils/patch";

patch(ClosePosPopup.prototype, {

    async confirm() {
        if (!this.pos.config.cash_control || this.env.utils.floatIsZero(this.getMaxDifference())) {
            await this.closeSession();
            return;
        }
        if (this.hasUserAuthority()) {
            let bodyMessage;
            if (this.pos.config.enable_approval) {
                bodyMessage = _t("Approval will be required for you to close session");
            } else {
                bodyMessage = _t("Do you want to accept payments difference and post a profit/loss journal entry?");
            }

            const { confirmed } = await this.popup.add(ConfirmPopup, {
                title: _t("Payments Difference"),
                body: _t(bodyMessage),
            });

            if (confirmed) {
                if(this.pos.config.enable_approval){
                    console.log('We have temporarily Suspended this --', this.props)
                    this.postApproval()
                }else {
                    await this.closeSession();
                }
            }
            return;
        }
    },

    async postApproval() {
        try {
        const bankPaymentMethodDiffPairs = this.props.other_payment_methods
                .filter((pm) => pm.type == "bank")
                .map((pm) => [pm.id, this.getDifference(pm.id)]);
        const response = await this.orm.call(
            "pos.session",
            "post_close_session_approval",
            [{
                "pos_session_id": this.pos.pos_session.id,
                "enable_approval": this.pos.config.enable_approval,
                "approval_level": this.pos.config.approval_level,
                "roles": this.pos.config.roles,
                "cash_difference": this.getMaxDifference(),
                "notes": this.state.notes,
                "payment_methods": bankPaymentMethodDiffPairs,
                "counted_cash": parseFloat(
                        this.state.payments[this.props.default_cash_details.id].counted
                    )},

            ]
        );
        console.log('Response from RPC:', response);
        window.location = "/web#action=point_of_sale.action_client_pos_menu";
    } catch (error) {
        console.error('Error calling post_close_session_approval:', error);
    }
   }

});