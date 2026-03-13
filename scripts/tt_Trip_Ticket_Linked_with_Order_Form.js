frappe.ui.form.on('Trip Ticket', {
    on_submit: function(frm) {
        // Loop through each row in the Trip Ticket table
        frm.doc.trip_ticket_table.forEach(function(row) {
            if(row.sales_no) {
                // Look up the Order Form via the Sales record's order_ref, then stamp the trip_ticket
                frappe.db.get_value('Sales', row.sales_no, 'order_ref').then(function(r) {
                    const order_ref = r && r.message && r.message.order_ref;
                    if (order_ref) {
                        frappe.db.set_value('Order Form', order_ref, 'trip_ticket', frm.doc.name)
                        .then(() => {
                            console.log('Order Form ' + order_ref + ' updated with Trip Ticket ' + frm.doc.name);
                        });
                    }
                });
            }
        });
    }
});
