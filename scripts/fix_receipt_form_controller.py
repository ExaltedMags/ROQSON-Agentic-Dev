"""
Redeploy Receipt: Form Controller without Unicode box-drawing comment chars.
Those chars are valid JS but can cause encoding issues on Windows console.
"""
import sys
sys.path.insert(0, ".")
import roqson

new_script = r"""// Receipt: Form Controller
// Handles auto-fill, payment field toggling, and Apply To grid logic.

var CHECK_FIELDS  = ['bank', 'check_no', 'check_date', 'deposit_bank_account', 'deposit_date'];
var BT_FIELDS     = ['bt_bank_account', 'bt_ref_no'];

function toggle_payment_fields(frm) {
    var pt = frm.doc.payment_type;
    var is_check = (pt === 'Check');
    var is_bt    = (pt === 'Bank Transfer');

    frm.toggle_display(CHECK_FIELDS, is_check);
    frm.toggle_reqd(CHECK_FIELDS, is_check);
    frm.toggle_display(BT_FIELDS, is_bt);
    frm.toggle_reqd(BT_FIELDS, is_bt);
}

frappe.ui.form.on('Receipt', {

    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('user', frappe.session.user);
        }
        toggle_payment_fields(frm);
    },

    refresh: function(frm) {
        toggle_payment_fields(frm);

        frm.set_query('customer', function() {
            return { doctype: 'Customer Information' };
        });

        frm.set_query('sales_no', 'apply_to', function() {
            return {
                filters: {
                    status: 'Received',
                    customer_link: frm.doc.customer || ''
                }
            };
        });
    },

    payment_type: function(frm) {
        toggle_payment_fields(frm);
    },

    customer: function(frm) {
        frm.refresh_field('apply_to');
    },

});

frappe.ui.form.on('Receipt Apply To', {

    sales_no: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (!row.sales_no) return;

        frappe.db.get_value('Sales', row.sales_no,
            ['creation_date', 'grand_total', 'outstanding_balance'],
            function(vals) {
                if (!vals) return;
                frappe.model.set_value(cdt, cdn, 'sale_date',        vals.creation_date || '');
                frappe.model.set_value(cdt, cdn, 'sale_grand_total', vals.grand_total || 0);
                frappe.model.set_value(cdt, cdn, 'outstanding_balance',
                    vals.outstanding_balance != null ? vals.outstanding_balance : vals.grand_total);
            }
        );
    },

    amount_applied: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        var preview = (row.sale_grand_total || 0) - (row.amount_applied || 0);
        if (preview < 0) preview = 0;
        frappe.model.set_value(cdt, cdn, 'outstanding_balance', preview);

        var total = 0;
        (frm.doc.apply_to || []).forEach(function(r) {
            total += r.amount_applied || 0;
        });
        frm.set_value('net_amount', total);
    },

});
"""

roqson.update_doc("Client Script", "Receipt: Form Controller", {"script": new_script})

body = roqson.get_script_body("Client Script", "Receipt: Form Controller")
issues = []
if r"\!" in body:    issues.append("\\! found")
if "..$wrapper" in body: issues.append("double-dot found")
if "!" not in body:  issues.append("! missing")

if issues:
    print("ISSUES: " + str(issues))
else:
    print("OK: Receipt: Form Controller clean, length=" + str(len(body)))
