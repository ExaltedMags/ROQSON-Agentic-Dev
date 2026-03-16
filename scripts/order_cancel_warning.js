// Sub-task 4: Warn user if cancelling an Order that has a linked Sales record
frappe.listview_settings["Order Form"] = frappe.listview_settings["Order Form"] || {};

(function() {
    var _orig_onload = frappe.listview_settings["Order Form"].onload;

    frappe.ui.form.on("Order Form", {
        before_workflow_action(frm) {
            return new Promise(function(resolve, reject) {
                var action = frm.selected_workflow_action;
                if (action !== "Cancel") {
                    resolve();
                    return;
                }
                var sales_ref = frm.doc.sales_ref;
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
    });
})();
