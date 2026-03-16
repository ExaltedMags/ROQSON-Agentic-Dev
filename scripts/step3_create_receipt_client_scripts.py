"""
Step 3 — Create Receipt Client Scripts
Creates:
  A. Receipt: Form Controller   (DocType: Receipt)
  B. Sales: Receipts Section    (DocType: Sales)
"""

import roqson
import requests
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": "token " + key + ":" + secret}
BASE = "https://roqson-industrial-sales.s.frappe.cloud"


def upsert_client_script(name, doctype, script_body):
    payload = {
        "doctype": "Client Script",
        "name": name,
        "dt": doctype,
        "script": script_body,
        "enabled": 1,
    }
    try:
        roqson.get_doc("Client Script", name)
        roqson.update_doc("Client Script", name, payload)
        print("Updated: " + name)
    except Exception:
        r = requests.post(BASE + "/api/resource/Client Script", json=payload, headers=headers)
        if r.status_code not in (200, 201):
            print("ERROR creating " + name + ": " + str(r.status_code))
            print(r.text[:500])
            raise Exception("Client Script creation failed: " + name)
        print("Created: " + name)


# ─────────────────────────────────────────────────────────────────────────────
# Client Script A — Receipt: Form Controller
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_A_NAME = "Receipt: Form Controller"

script_a_body = """// Receipt: Form Controller
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
"""

upsert_client_script(SCRIPT_A_NAME, "Receipt", script_a_body)


# ─────────────────────────────────────────────────────────────────────────────
# Client Script B — Sales: Receipts Section
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_B_NAME = "Sales: Receipts Section"

script_b_body = """// Sales: Receipts Section
// Renders the posted receipts table on the Sales form.
// Also removes any residual manual Completed buttons (belt-and-suspenders).

frappe.ui.form.on('Sales', {

    refresh: function(frm) {
        if (!frm.is_new()) {
            remove_manual_completed_gate(frm);
            render_receipts_section(frm);
        }
    },

});

function remove_manual_completed_gate(frm) {
    // Remove any manual Completed buttons that may have been added elsewhere
    frm.page.remove_inner_button('Mark as Completed');
    frm.page.remove_inner_button('Mark Completed');
    frm.page.remove_inner_button('Accounting');
}

function render_receipts_section(frm) {
    var html_field = frm.get_field('receipts_html');
    if (!html_field) return;

    frappe.call({
        method: 'frappe.client.get_list',
        args: {
            doctype: 'Receipt Apply To',
            filters: [
                ['sales_no',  '=', frm.doc.name],
                ['docstatus', '=', 1]
            ],
            fields: ['name', 'parent', 'amount_applied', 'outstanding_balance'],
            limit: 200
        },
        callback: function(r) {
            var rows = (r && r.message) ? r.message : [];

            if (!rows.length) {
                html_field.$wrapper.html(
                    '<div style="color:#6b7280;font-style:italic;padding:8px 0;">No receipts posted yet.</div>'
                );
                return;
            }

            // Fetch parent Receipt docs for date/payment_type/user
            var parent_names = rows.map(function(r) { return r.parent; });
            var unique_parents = parent_names.filter(function(v, i, a) { return a.indexOf(v) === i; });

            frappe.call({
                method: 'frappe.client.get_list',
                args: {
                    doctype: 'Receipt',
                    filters: [['name', 'in', unique_parents]],
                    fields: ['name', 'date', 'payment_type', 'user'],
                    limit: 200
                },
                callback: function(rp) {
                    var parents = {};
                    ((rp && rp.message) ? rp.message : []).forEach(function(p) {
                        parents[p.name] = p;
                    });

                    var html = '<table class="table table-bordered table-condensed" style="font-size:12px;margin-bottom:0;">'
                        + '<thead><tr>'
                        + '<th>Receipt No.</th>'
                        + '<th>Date</th>'
                        + '<th>Payment Type</th>'
                        + '<th>Amount Applied</th>'
                        + '<th>Posted By</th>'
                        + '</tr></thead><tbody>';

                    rows.forEach(function(row) {
                        var p = parents[row.parent] || {};
                        var link = '<a href="/app/receipt/' + row.parent + '">' + row.parent + '</a>';
                        html += '<tr>'
                            + '<td>' + link + '</td>'
                            + '<td>' + (p.date || '') + '</td>'
                            + '<td>' + (p.payment_type || '') + '</td>'
                            + '<td style="text-align:right;">' + frappe.format(row.amount_applied, {fieldtype:'Currency'}) + '</td>'
                            + '<td>' + (p.user || '') + '</td>'
                            + '</tr>';
                    });

                    html += '</tbody></table>';
                    html_field.$wrapper.html(html);
                }
            });
        }
    });
}
"""

upsert_client_script(SCRIPT_B_NAME, "Sales", script_b_body)


# ── Verify ────────────────────────────────────────────────────────────────────
print("\nVerifying client scripts...")
result_r = roqson.get_scripts_for_doctype("Receipt")
print("Receipt client scripts: " + str(len(result_r.get("client", []))))
for s in result_r.get("client", []):
    print("  - " + s["name"] + " | enabled: " + str(s.get("enabled")))

result_s = roqson.get_scripts_for_doctype("Sales")
sales_scripts = [s["name"] for s in result_s.get("client", [])]
print("Sales client scripts: " + str(sales_scripts))
