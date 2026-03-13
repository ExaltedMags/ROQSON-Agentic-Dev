import roqson

script_name = "Order Form: Table Management & Calculation"
old_script = roqson.get_script_body("Client Script", script_name)

# Find where "Set All Warehouses Button" is added and insert the Unreserve button logic right after it.
insertion_point = "d.show();\n            });\n        }"

unreserve_button_code = """
        // --- Unreserve/Reserve Selected Items ---
        if (frm.fields_dict.table_mkaq && frm.fields_dict.table_mkaq.grid) {
            frm.fields_dict.table_mkaq.grid.add_custom_button(__('Toggle Unreserve Selected'), () => {
                const selected = frm.fields_dict.table_mkaq.grid.get_selected_children();
                if (!selected || selected.length === 0) {
                    frappe.msgprint(__('Please select at least one row to unreserve/reserve.'));
                    return;
                }
                
                let changed = false;
                selected.forEach(row => {
                    const current_val = row.unreserved || 0;
                    frappe.model.set_value(row.doctype, row.name, 'unreserved', current_val ? 0 : 1);
                    changed = true;
                });
                
                if (changed) {
                    frm.refresh_field('table_mkaq');
                    frappe.show_alert({ message: __('Reserve status toggled for selected items. Please save to apply.'), indicator: 'orange' });
                }
            });
        }
"""

new_script = old_script.replace(insertion_point, insertion_point + "\n" + unreserve_button_code)

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
