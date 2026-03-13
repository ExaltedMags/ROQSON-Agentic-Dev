import roqson
import sys

# 1. Update Client Script for Order Form
order_client_script = """
frappe.ui.form.on("Order Form", {
    before_workflow_action(frm) {
        var action = frm.selected_workflow_action;
        if (action !== "Cancel") {
            return;
        }

        return new Promise(function(resolve, reject) {
            frappe.db.get_list("Sales", {
                filters: { order_ref: frm.doc.name, status: ["!=", "Cancelled"] },
                fields: ["name"]
            }).then(records => {
                if (records && records.length > 0) {
                    var sales_ref = records[0].name;
                    frappe.confirm(
                        __("This order has a linked Sales record ({0}). Cancelling this order will also cancel the Sales record. Proceed?", [sales_ref]),
                        function() { resolve(); },
                        function() { reject("Cancelled by user."); }
                    );
                } else {
                    resolve();
                }
            });
        });
    }
});
"""

print("Updating Client Script: Order Form: Cancel Sales Warning")
roqson.update_doc("Client Script", "Order Form: Cancel Sales Warning", {
    "script": order_client_script,
    "enabled": 1
})

# 2. Update Server Script for Order Form Auto Cancel
order_server_script = """
# Auto Cancel Sales on Order Cancellation
# DocType Event: Order Form — After Save (Submitted Document)

old_doc = doc.get_doc_before_save()
if not old_doc:
    old_wf = ""
else:
    old_wf = old_doc.workflow_state or ""

# Only trigger on transition TO Canceled
if doc.workflow_state == "Canceled" and old_wf != "Canceled":
    sales_records = frappe.get_all("Sales", filters={"order_ref": doc.name, "status": ["!=", "Cancelled"]})
    if sales_records:
        sales_ref = sales_records[0].name
        frappe.db.set_value("Sales", sales_ref, "status", "Cancelled")
"""

print("Updating Server Script: Auto Cancel Sales on Order Cancellation")
roqson.update_doc("Server Script", "Auto Cancel Sales on Order Cancellation", {
    "script": order_server_script,
    "disabled": 0
})


# 3. Create Client Script for Sales Form Warning and Permissions
sales_client_script = """
frappe.ui.form.on("Sales", {
    refresh(frm) {
        frm._last_status = frm.doc.status;
    },
    validate(frm) {
        if (frm.doc.status === "Cancelled" && frm._last_status !== "Cancelled") {
            // Check role permissions
            const user_roles = frappe.user_roles;
            const can_cancel = user_roles.includes("Sales") || 
                               user_roles.includes("Sales Manager") || 
                               user_roles.includes("Sales User") || 
                               user_roles.includes("System Manager") || 
                               user_roles.includes("Administrator");
            
            if (!can_cancel) {
                frappe.msgprint({
                    title: __('Permission Denied'),
                    indicator: 'red',
                    message: __('Only Sales role and Admin can cancel a Sales record directly.')
                });
                frappe.validated = false;
                frm.set_value('status', frm._last_status);
                return;
            }

            if (frm.doc.order_ref && !frm.doc.__cancel_confirmed) {
                frappe.validated = false;
                frappe.confirm(
                    __("Cancelling this Sales record will also cancel the linked Order ({0}). Proceed?", [frm.doc.order_ref]),
                    function() {
                        frm.doc.__cancel_confirmed = true;
                        frm.save();
                    },
                    function() {
                        frm.set_value('status', frm._last_status);
                    }
                );
            }
        }
    }
});
"""

print("Looking for or creating Client Script: Sales: Cancel Warning")
import requests
import json
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": f"token {key}:{secret}"}

client_doc = {
    "doctype": "Client Script",
    "name": "Sales: Cancel Warning",
    "dt": "Sales",
    "script": sales_client_script,
    "enabled": 1
}
try:
    roqson.update_doc("Client Script", "Sales: Cancel Warning", client_doc)
    print("Updated Sales: Cancel Warning")
except Exception:
    r = requests.post("https://roqson-industrial-sales.s.frappe.cloud/api/resource/Client Script", json=client_doc, headers=headers)
    print("Created Sales: Cancel Warning:", r.status_code)

# 4. Create Server Script for Sales Auto Cancel
sales_server_script = """
# Auto Cancel Order on Sales Cancellation
# DocType Event: Sales - Before Save

old_doc = doc.get_doc_before_save()
old_status = old_doc.status if old_doc else ""

if doc.status == "Cancelled" and old_status != "Cancelled":
    # Role validation
    allowed_roles = ["Sales", "Sales Manager", "Sales User", "System Manager", "Administrator"]
    user_roles = frappe.get_roles(frappe.session.user)
    has_permission = False
    for r in allowed_roles:
        if r in user_roles:
            has_permission = True
            break
            
    if not has_permission:
        frappe.throw("Only Sales role and Admin can cancel a Sales record directly.")

    if doc.order_ref:
        order_doc = frappe.get_doc("Order Form", doc.order_ref)
        if order_doc.workflow_state != "Canceled":
            order_doc.workflow_state = "Canceled"
            order_doc.save(ignore_permissions=True)
"""

print("Looking for or creating Server Script: Auto Cancel Order on Sales Cancellation")
server_doc = {
    "doctype": "Server Script",
    "name": "Auto Cancel Order on Sales Cancellation",
    "script_type": "DocType Event",
    "reference_doctype": "Sales",
    "doctype_event": "Before Save",
    "script": sales_server_script,
    "disabled": 0
}
try:
    roqson.update_doc("Server Script", "Auto Cancel Order on Sales Cancellation", server_doc)
    print("Updated Auto Cancel Order on Sales Cancellation")
except Exception:
    r = requests.post("https://roqson-industrial-sales.s.frappe.cloud/api/resource/Server Script", json=server_doc, headers=headers)
    print("Created Auto Cancel Order on Sales Cancellation:", r.status_code)

print("Done")
