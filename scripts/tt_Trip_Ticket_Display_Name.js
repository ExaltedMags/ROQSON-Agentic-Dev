frappe.ui.form.on('Trip Ticket', {
    onload: function(frm) {
        let grid = frm.fields_dict['table_cpme'].grid;

        grid.get_field('sales_no').formatter = function(value, doc) {
            if (!value) return value;

            return value + (doc.outlet_name ? ' – ' + doc.outlet_name : '');
        }
    }
});
