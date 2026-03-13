import roqson

script_name = "Sales: Form Logic & Calculations"
old_script = roqson.get_script_body("Client Script", script_name)

insertion_point = "grid.refresh();\n        }"

unreserve_button_code = """
        // --- Unreserve/Reserve Selected Items ---
        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            frm.fields_dict.items.grid.add_custom_button(__('Toggle Unreserve Selected'), () => {
                const selected = frm.fields_dict.items.grid.get_selected_children();
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
        }
"""

new_script = old_script.replace(insertion_point, insertion_point + "\n" + unreserve_button_code)

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
