frappe.ui.form.on('Trip Ticket Table', {
    onload: function(frm) {
        frm.fields_dict['trip_ticket_table'].grid.get_field('sales_no').get_query = function(doc, cdt, cdn) {
            return {
                filters: {},               // optional filters
                order_by: 'creation desc'  // newest first
            };
        };
    }
});
