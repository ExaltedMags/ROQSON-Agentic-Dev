import roqson

script_name = "Trip Ticket: Print Billing Statement"

script_code = """
frappe.ui.form.on('Trip Ticket', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            const allowed_roles = [
                'Administrator', 'System Manager', 
                'Stock Manager', 'Stock User', 
                'Dispatcher', 'Driver',
                'Manager', 'President'
            ];
            
            const has_access = allowed_roles.some(role => frappe.user.has_role(role));
            
            if (has_access) {
                // 1. Add to the standard toolbar for visibility
                frm.add_custom_button(__('Billing Statement'), function() {
                    frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                }, __("Print"));

                // 2. Also add it as a standalone primary-style button in the toolbar (most visible)
                frm.add_custom_button(__('Print Billing Statement'), function() {
                    frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                });

                // 3. Coordinate placement with the detail page timeline buttons
                frm.trigger('inject_print_button_to_html');
            }
        }
    },

    inject_print_button_to_html: function(frm) {
        const HTML_FIELD = 'custom_delivery_timeline_controls';
        const htmlField = frm.fields_dict[HTML_FIELD];
        
        if (htmlField && htmlField.$wrapper) {
            // Wait for existing UI to stabilize
            setTimeout(() => {
                if (htmlField.$wrapper.find('.tt-print-billing-injected').length === 0) {
                    const btnHtml = `
                        <button class="btn btn-default btn-lg tt-print-billing-injected" style="min-width:220px; border: 1px solid #d1d8dd; margin-left: 0px;">
                            <i class="fa fa-print"></i> Print Billing Statement
                        </button>
                    `;
                    // Look for the flex container created by the timeline script
                    const container = htmlField.$wrapper.find('div[style*="display:flex"]');
                    if (container.length > 0) {
                        $(container[0]).append(btnHtml);
                        htmlField.$wrapper.find('.tt-print-billing-injected').on('click', () => {
                            frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                        });
                    }
                }
            }, 800);
        }
    }
});
"""

doc = {
    "doctype": "Client Script",
    "name": script_name,
    "dt": "Trip Ticket",
    "view": "Form",
    "script": script_code,
    "enabled": 1,
    "module": "Core"
}

try:
    existing = roqson.get_doc("Client Script", script_name)
    roqson.update_doc("Client Script", script_name, {"script": script_code, "enabled": 1})
    print(f"Updated Client Script: {script_name}")
except Exception as e:
    res = roqson.call_method("frappe.client.insert", doc=doc)
    print(f"Created Client Script: {script_name}")
