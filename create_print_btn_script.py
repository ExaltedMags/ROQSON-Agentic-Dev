import roqson

script_name = "Trip Ticket: Print Billing Statement"

script_code = """
frappe.ui.form.on('Trip Ticket', {
    refresh: function(frm) {
        if (!frm.is_new()) {
            const roles = frappe.user_roles;
            const allowed_roles = [
                'Administrator', 'System Manager', 
                'Stock Manager', 'Stock User', 
                'Dispatcher', 'Driver'
            ];
            
            const has_access = allowed_roles.some(r => roles.includes(r));
            const is_restricted = roles.includes('Sales') || roles.includes('DSP');
            
            // Allow if user has an allowed role. If they only have restricted roles, block.
            // Admins with multiple roles will still see it.
            if (has_access || (!is_restricted && roles.length > 0)) {
                frm.add_custom_button(__('Print Billing Statement'), function() {
                    frappe.set_route("print", frm.doc.doctype, frm.doc.name, "Billing Statement");
                });
                
                // Also hide pricing-related elements if any exist, though the Billing Statement format handles this by not showing prices.
            }
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
