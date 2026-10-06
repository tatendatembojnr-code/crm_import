/** @odoo-module **/

import { registry } from "@web/core/registry";
import { formView } from "@web/views/form/form_view";
import { FormController } from "@web/views/form/form_controller";

export class CrmLeadFormController extends FormController {
    async save(params) {
        const record = this.model.root;
        const saved = await super.save(params);
        if (saved && record.resModel === "crm.lead" && record.resId) {
            // If lead is active and has no next contact date, pop up the Activity Schedule dialog
            if (record.data.active && !record.data.custom_next_contact_date) {
                await this.actionService.doAction({
                    type: "ir.actions.act_window",
                    name: "Schedule an Activity",
                    res_model: "mail.activity.schedule",
                    view_mode: "form",
                    views: [[false, "form"]],
                    target: "new",
                    context: {
                        active_model: "crm.lead",
                        active_id: record.resId,
                        active_ids: [record.resId],
                        default_summary: "To-Do",
                        default_note: "<p>Next Contact Date</p>",
                        dialog_size: "large",
                    },
                }, {
                    onClose: async () => {
                        await record.load();
                    },
                });
            }
        }
        return saved;
    }
}

export const crmLeadFormView = {
    ...formView,
    Controller: CrmLeadFormController,
};

registry.category("views").add("crm_lead_form", crmLeadFormView);
