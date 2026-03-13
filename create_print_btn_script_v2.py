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
                // Add to standard toolbar
                frm.add_custom_button(__('Print Billing Statement'), function() {
                    frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                }, __("Print"));

                // Also attempt to inject into the big button area if it exists
                frm.trigger('inject_print_button_to_html');
            }
        }
    },

    inject_print_button_to_html: function(frm) {
        const HTML_FIELD = 'custom_delivery_timeline_controls';
        const htmlField = frm.fields_dict[HTML_FIELD];
        
        if (htmlField && htmlField.$wrapper) {
            // Wait a bit for the other script to finish rendering its buttons
            setTimeout(() => {
                if (htmlField.$wrapper.find('.tt-print-billing').length === 0) {
                    const btnHtml = `
                        <button class="btn btn-default btn-lg tt-print-billing" style="min-width:220px; border: 1px solid #d1d8dd;">
                            <i class="fa fa-print"></i> Print Billing Statement
                        </button>
                    `;
                    // Append to the flex container if it exists
                    const container = htmlField.$wrapper.find('div[style*="display:flex"]');
                    if (container.length > 0) {
                        $(container[0]).append(btnHtml);
                        htmlField.$wrapper.find('.tt-print-billing').on('click', () => {
                            frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                        });
                    }
                }
            }, 500);
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
    print("Found existing script, updating...")
    roqson.update_doc("Client Script", script_name, {"script": script_code, "enabled": 1})
    print(f"Updated Client Script: {script_name}")
except Exception as e:
    print("Creating new Client Script...")
    res = roqson.call_method("frappe.client.insert", doc=doc)
    print(f"Created Client Script: {script_name}")
