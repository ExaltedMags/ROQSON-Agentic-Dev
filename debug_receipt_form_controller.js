// Receipt: Form Controller
// Handles auto-fill, payment field toggling, and Apply To grid logic.

// ── Payment field groups ────────────────────────────────────────────────────
var CHECK_FIELDS  = ['bank', 'check_no', 'check_date', 'deposit_bank_account', 'deposit_date'];
var BT_FIELDS     = ['bt_bank_account', 'bt_ref_no'];
var ALL_PAY_FIELDS = CHECK_FIELDS.concat(BT_FIELDS);

function toggle_payment_fields(frm) {
    var pt = frm.doc.payment_type;
    var is_check = (pt === 'Check');
    var is_bt    = (pt === 'Bank Transfer');

    frm.toggle_display(CHECK_FIELDS, is_check);
    frm.toggle_reqd(CHECK_FIELDS, is_check);
    frm.toggle_display(BT_FIELDS, is_bt);
    frm.toggle_reqd(BT_FIELDS, is_bt);
}

// ── Form events ─────────────────────────────────────────────────────────────
frappe.ui.form.on('Receipt', {

    onload: function(frm) {
        if (frm.is_new()) {
            frm.set_value('user', frappe.session.user);
        }
        toggle_payment_fields(frm);
    },

    refresh: function(frm) {
        toggle_payment_fields(frm);

        // Filter customer Link
        frm.set_query('customer', function() {
            return { doctype: 'Customer Information' };
        });

        // Filter sales_no in Apply To grid
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
        // Refresh Apply To grid so sales_no filter updates
        frm.refresh_field('apply_to');
    },

});

// ── Child table events ───────────────────────────────────────────────────────
frappe.ui.form.on('Receipt Apply To', {

    sales_no: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        if (!row.sales_no) return;

        frappe.db.get_value('Sales', row.sales_no,
            ['creation_date', 'grand_total', 'outstanding_balance'],
            function(vals) {
                if (!vals) return;
                frappe.model.set_value(cdt, cdn, 'sale_date',        vals.creation_date    || '');
                frappe.model.set_value(cdt, cdn, 'sale_grand_total', vals.grand_total       || 0);
                frappe.model.set_value(cdt, cdn, 'outstanding_balance', vals.outstanding_balance != null
                    ? vals.outstanding_balance : vals.grand_total);
            }
        );
    },

    amount_applied: function(frm, cdt, cdn) {
        var row = locals[cdt][cdn];
        // Client-side preview of row outstanding
        var preview_outstanding = (row.sale_grand_total || 0) - (row.amount_applied || 0);
        if (preview_outstanding < 0) preview_outstanding = 0;
        frappe.model.set_value(cdt, cdn, 'outstanding_balance', preview_outstanding);

        // Update net_amount header as sum of all amount_applied rows
        var total = 0;
        (frm.doc.apply_to || []).forEach(function(r) {
            total += r.amount_applied || 0;
        });
        frm.set_value('net_amount', total);
    },

});
