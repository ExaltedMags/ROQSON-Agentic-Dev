// Sales: Receipts Section
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
    frm.page.remove_inner_button('Mark as Completed');
    frm.page.remove_inner_button('Mark Completed');
    frm.page.remove_inner_button('Accounting');
}

function render_receipts_section(frm) {
    var html_field = frm.get_field('receipts_html');
    if (!html_field) return;

    html_field.$wrapper.html('<div style="color:#9ca3af;font-size:12px;padding:4px 0;">Loading receipts...</div>');

    frappe.call({
        method: 'get_receipt_history_for_sale',
        args: { sales_no: frm.doc.name },
        callback: function(r) {
            var rows = (r && r.message) ? r.message : [];

            if (!rows.length) {
                html_field.$wrapper.html(
                    '<div style="color:#6b7280;font-style:italic;padding:8px 0;">No receipts posted yet.</div>'
                );
                return;
            }

            var html = '<table class="table table-bordered table-condensed" style="font-size:12px;margin-bottom:0;">'
                + '<thead><tr>'
                + '<th>Receipt No.</th>'
                + '<th>Date</th>'
                + '<th>Payment Type</th>'
                + '<th style="text-align:right;">Amount Applied</th>'
                + '<th>Posted By</th>'
                + '</tr></thead><tbody>';

            rows.forEach(function(row) {
                var link = '<a href="/app/receipt/' + row.receipt_no + '">' + row.receipt_no + '</a>';
                html += '<tr>'
                    + '<td>' + link + '</td>'
                    + '<td>' + (row.date || '') + '</td>'
                    + '<td>' + (row.payment_type || '') + '</td>'
                    + '<td style="text-align:right;">' + frappe.format(row.amount_applied, {fieldtype: 'Currency'}) + '</td>'
                    + '<td>' + (row.user || '') + '</td>'
                    + '</tr>';
            });

            html += '</tbody></table>';
            html_field.$wrapper.html(html);
        },
        error: function() {
            html_field.$wrapper.html(
                '<div style="color:#9ca3af;font-style:italic;padding:8px 0;">Could not load receipts.</div>'
            );
        }
    });
}
