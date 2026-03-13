import roqson

script_name = "Sales: Form Logic & Calculations"
old_script = roqson.get_script_body("Client Script", script_name)

old_logic = """            // Only allow Unreserve toggling on Pending or Failed Sales
            if (frm.doc.status === 'Pending' || frm.doc.status === 'Failed') {
                grid.add_custom_button(__('Unreserve Selected'), () => {
                    const selected = grid.get_selected_children();
                    if (!selected || selected.length === 0) {
                        frappe.msgprint(__('Please select at least one row to unreserve/reserve.'));
                        return;
                    }
                    
                    let changed = false;
                    selected.forEach(row => {
                        const current_val = row.is_unreserved || 0;
                        frappe.model.set_value(row.doctype, row.name, 'is_unreserved', current_val ? 0 : 1);
                        changed = true;
                    });
                    
                    if (changed) {
                        frm.refresh_field('items');
                        frappe.show_alert({ message: __('Reserve status toggled for selected items. Please SAVE the document to apply changes.'), indicator: 'orange' });
                    }
                });
            }"""

new_logic = """            // Only allow Unreserve toggling on Pending or Failed Sales
            if (frm.doc.status === 'Pending' || frm.doc.status === 'Failed') {
                grid.add_custom_button(__('Unreserve Selected'), () => {
                    const selected = grid.get_selected_children();
                    if (!selected || selected.length === 0) {
                        frappe.msgprint(__('Please select at least one row.'));
                        return;
                    }
                    
                    let changed = false;
                    selected.forEach(row => {
                        if (!row.is_unreserved) {
                            frappe.model.set_value(row.doctype, row.name, 'is_unreserved', 1);
                            changed = true;
                        }
                    });
                    
                    if (changed) {
                        frm.refresh_field('items');
                        frappe.show_alert({ message: __('Unreserving items...'), indicator: 'orange' });
                        frm.save();
                    } else {
                        frappe.msgprint(__('Selected items are already unreserved.'));
                    }
                });

                grid.add_custom_button(__('Reserve Selected'), () => {
                    const selected = grid.get_selected_children();
                    if (!selected || selected.length === 0) {
                        frappe.msgprint(__('Please select at least one row.'));
                        return;
                    }
                    
                    let changed = false;
                    selected.forEach(row => {
                        if (row.is_unreserved) {
                            frappe.model.set_value(row.doctype, row.name, 'is_unreserved', 0);
                            changed = true;
                        }
                    });
                    
                    if (changed) {
                        frm.refresh_field('items');
                        frappe.show_alert({ message: __('Reserving items...'), indicator: 'blue' });
                        frm.save();
                    } else {
                        frappe.msgprint(__('Selected items are already reserved.'));
                    }
                });
            }"""

if old_logic in old_script:
    new_script = old_script.replace(old_logic, new_logic)
    roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
else:
    print("Old logic block not found in script.")
