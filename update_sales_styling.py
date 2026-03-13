import roqson

new_script = """
// Sales: Status Validation & List View
// Blocks marking a Sales record as Paid unless at least one file is attached.

frappe.ui.form.on('Sales', {
    status: function(frm) {
        // 'Completed' is now the target status for fully paid (verified by receipts)
        if (frm.doc.status === 'Completed' && !frm.is_new()) {
            // Check attached files via server
            frappe.db.get_list('File', {
                filters: {
                    attached_to_doctype: 'Sales',
                    attached_to_name: frm.doc.name
                },
                fields: ['name'],
                limit: 1
            }).then(files => {
                if (!files || !files.length) {
                    frappe.msgprint({
                        title: 'Receipt Required',
                        message: 'Please attach at least one receipt file before marking this record as Completed. Use the paperclip button at the bottom of the form.',
                        indicator: 'red'
                    });
                    // Fallback to previous status if possible, or Pending
                    frappe.model.set_value(frm.doctype, frm.docname, 'status', 'Pending');
                }
            });
        }
    },

    before_save: function(frm) {
        if (frm.doc.status === 'Completed' && !frm.is_new()) {
            return new Promise((resolve, reject) => {
                frappe.db.get_list('File', {
                    filters: {
                        attached_to_doctype: 'Sales',
                        attached_to_name: frm.doc.name
                    },
                    fields: ['name'],
                    limit: 1
                }).then(files => {
                    if (!files || !files.length) {
                        frappe.msgprint({
                            title: 'Receipt Required',
                            message: 'Cannot save as Completed: no receipt files attached. Attach a receipt first.',
                            indicator: 'red'
                        });
                        reject('No receipt attached');
                    } else {
                        resolve();
                    }
                });
            });
        }
    }
});

// ── Status badge color map for Sales ───────────────────────────────────────────
const SALES_STATE_COLORS = {
    "Pending":     { bg: "#FEFCE8", text: "#854D0E", border: "rgba(133, 77, 14, 0.15)" },  // Yellow
    "Dispatching": { bg: "#F0FDFA", text: "#134E4A", border: "rgba(19, 78, 74, 0.15)" },  // Teal
    "In Transit":  { bg: "#EFF6FF", text: "#1E40AF", border: "rgba(30, 64, 175, 0.15)" },  // Blue
    "Received":    { bg: "#F0FDF4", text: "#166534", border: "rgba(22, 101, 52, 0.15)" },  // Green
    "Failed":      { bg: "#FEF2F2", text: "#991B1B", border: "rgba(153, 27, 27, 0.15)" },  // Red
    "Completed":   { bg: "#ECFDF5", text: "#065F46", border: "rgba(6, 95, 70, 0.15)" },   // Emerald/Deep Green
    "Cancelled":   { bg: "#FFF1F2", text: "#9F1239", border: "rgba(159, 18, 57, 0.15)" },  // Rose/Red
};

function sales_badge_html(colors, label) {
    const style = [
        `background-color:${colors.bg}`,
        `color:${colors.text}`,
        `border:1px solid ${colors.border}`,
        `border-radius:9999px`,
        `padding:2px 10px`,
        `font-size:11px`,
        `font-weight:600`,
        `white-space:nowrap`,
        `display:inline-block`,
        `line-height:1.4`,
    ].join(';');
    return `<span style="${style}">${label}</span>`;
}

// List view configuration: Advanced layout and styling
frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date'],

    get_indicator: function(doc) {
        // Default Frappe indicator colors as fallback
        const map = {
            'Pending':     ['orange'],
            'Dispatching': ['cyan'],
            'In Transit':  ['blue'],
            'Received':    ['green'],
            'Failed':      ['red'],
            'Completed':   ['emerald'],
            'Cancelled':   ['grey'],
        };
        return [doc.status, map[doc.status] || 'grey', `status,=,${doc.status}`];
    },

    formatters: {
        status(value, field, doc) {
            if (!value) return value;
            let colors = SALES_STATE_COLORS[value];
            if (!colors) return value;
            return sales_badge_html(colors, value);
        }
    },

    onload(listview) {
        this.inject_css();
    },

    refresh(listview) {
        this.style_columns(listview);
    },

    inject_css() {
        if (document.getElementById('sales-list-css')) return;
        const style = document.createElement('style');
        style.id = 'sales-list-css';
        style.textContent = `
            /* Style the columns with specific widths */
            #page-List\\/Sales\\/List .list-subject {
                flex: 0 0 140px !important; min-width: 140px !important; max-width: 140px !important;
                font-weight: bold;
            }

            #page-List\\/Sales\\/List .sales-col-status { 
                flex: 0 0 130px !important; min-width: 130px !important; 
                display: flex !important; align-items: center;
            }
            #page-List\\/Sales\\/List .sales-col-customer { flex: 0 0 200px !important; min-width: 200px !important; }
            #page-List\\/Sales\\/List .sales-col-address { flex: 0 0 200px !important; min-width: 200px !important; }
            #page-List\\/Sales\\/List .sales-col-total { flex: 0 0 120px !important; min-width: 120px !important; text-align: right; }
            #page-List\\/Sales\\/List .sales-col-order { flex: 0 0 140px !important; min-width: 140px !important; }
            #page-List\\/Sales\\/List .sales-col-date { flex: 0 0 120px !important; min-width: 120px !important; }

            #page-List\\/Sales\\/List .list-row-head,
            #page-List\\/Sales\\/List .list-row-container .list-row {
                min-width: 1050px !important;
                display: flex !important;
                flex-wrap: nowrap !important;
            }
            #page-List\\/Sales\\/List .result { overflow-x: auto !important; }

            /* Set header label for ID column (Subject) */
            #page-List\\/Sales\\/List .list-row-head .list-subject .level-item {
                display: none !important;
            }
            #page-List\\/Sales\\/List .list-row-head .list-subject:after {
                content: "ID";
                font-weight: bold;
                padding-left: 10px;
            }
        `;
        document.head.appendChild(style);
    },

    style_columns(listview) {
        const page = listview.page.wrapper[0];
        const fieldClassMap = {
            'status': 'sales-col-status',
            'customer_link': 'sales-col-customer',
            'address': 'sales-col-address',
            'grand_total': 'sales-col-total',
            'order_ref': 'sales-col-order',
            'creation_date': 'sales-col-date'
        };

        // Map column classes based on fieldnames
        $(page).find('.list-row-head .list-row-col, .list-row-container .list-row .list-row-col').each(function() {
            const $col = $(this);
            const $filter = $col.find('[data-filter]');
            if ($filter.length) {
                const field = $filter.attr('data-filter').split(',')[0];
                if (fieldClassMap[field]) $col.addClass(fieldClassMap[field]);
            } else {
                // Fallback to text matching for headers if filters are not present
                const text = $col.text().trim();
                if (text === 'Status') $col.addClass('sales-col-status');
                if (text === 'Customer') $col.addClass('sales-col-customer');
                if (text === 'Address') $col.addClass('sales-col-address');
                if (text === 'Grand Total') $col.addClass('sales-col-total');
                if (text === 'Order Ref.') $col.addClass('sales-col-order');
                if (text === 'Date Created' || text === 'Creation') $col.addClass('sales-col-date');
            }
        });
    }
};
"""

roqson.update_doc("Client Script", "Sales: Paid Validation", {"script": new_script})
print("Updated Sales: Paid Validation list view styling")
