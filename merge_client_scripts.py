import roqson

# 1. Disable the colliding script
print("Disabling 'Order Form: Cancel Sales Warning'...")
roqson.update_doc("Client Script", "Order Form: Cancel Sales Warning", {"enabled": 0})

# 2. Fetch the Warehouse Assignment script
warehouse_doc = roqson.get_doc("Client Script", "Order Form: Warehouse Assignment")
old_script = warehouse_doc.get("script", "")

# 3. Create the unified header that handles both actions
new_header = """// Order Form: Workflow Action Interceptors (Merged)
// Consolidates before_workflow_action for Warehouse Assignment and Cancel Warning
// to prevent Frappe hook overwriting.

frappe.ui.form.on('Order Form', {
    before_workflow_action: function(frm) {
        const action = frm.selected_workflow_action;
        
        // 1. Warehouse Assignment
        if (action === 'Submit' || action === 'Approve') {
            return open_warehouse_assignment_dialog(frm, action);
        }
        
        // 2. Cancel Sales Warning
        if (action === 'Cancel') {
            return new Promise((resolve, reject) => {
                const sales_ref = frm.doc.sales_ref;
                if (!sales_ref) {
                    resolve();
                    return;
                }
                frappe.confirm(
                    __("This order has a linked Sales record ({0}). Cancelling the order will also cancel the Sales record. Proceed?", [sales_ref]),
                    function() { resolve(); },
                    function() { reject("Cancelled by user."); }
                );
            });
        }
    }
});
"""

# Extract the rest of the warehouse dialog logic
parts = old_script.split("function open_warehouse_assignment_dialog")
if len(parts) > 1:
    dialog_func = "function open_warehouse_assignment_dialog" + parts[1]
    final_script = new_header + "\n" + dialog_func
    
    print("Updating 'Order Form: Warehouse Assignment' with merged logic...")
    roqson.update_doc("Client Script", "Order Form: Warehouse Assignment", {"script": final_script})
    print("Merge complete!")
else:
    print("Failed to extract function from old script.")
