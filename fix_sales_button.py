import roqson
import requests
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}

new_sales_list_script = """
// Sales: Master List & Form Script
// Handles status validation, list view styling, and bundle actions.

frappe.ui.form.on('Sales', {
    status: function(frm) {
        if (frm.doc.status === 'Completed' && !frm.is_new()) {
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
                        message: 'Please attach at least one receipt file before marking this record as Completed.',
                        indicator: 'red'
                    });
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
                            message: 'Cannot save as Completed: no receipt files attached.',
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
    "Pending":     { bg: "#FEFCE8", text: "#854D0E", border: "rgba(133, 77, 14, 0.15)" },
    "Dispatching": { bg: "#F0FDFA", text: "#134E4A", border: "rgba(19, 78, 74, 0.15)" },
    "In Transit":  { bg: "#EFF6FF", text: "#1E40AF", border: "rgba(30, 64, 175, 0.15)" },
    "Received":    { bg: "#F0FDF4", text: "#166534", border: "rgba(22, 101, 52, 0.15)" },
    "Failed":      { bg: "#FEF2F2", text: "#991B1B", border: "rgba(153, 27, 27, 0.15)" },
    "Completed":   { bg: "#ECFDF5", text: "#065F46", border: "rgba(6, 95, 70, 0.15)" },
    "Cancelled":   { bg: "#FFF1F2", text: "#9F1239", border: "rgba(159, 18, 57, 0.15)" },
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

frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date', 'fulfillment_type'],

    get_indicator: function(doc) {
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
        
        // Add custom Address Filter
        if (!listview.page.fields_dict.address_filter) {
            listview.page.add_field({
                fieldname: 'address_filter',
                fieldtype: 'Data',
                label: 'Filter by Address',
                change: function() {
                    const val = this.get_value();
                    listview.filter_area.filter_list.filters
                        .filter(f => f.fieldname === 'address')
                        .forEach(f => f.remove());
                    
                    if (val) {
                        listview.filter_area.add([['Sales', 'address', 'like', '%' + val + '%']]);
                    }
                }
            });
        }
        
        // Listen for checkbox selection changes
        listview.$result.on('change', '.list-row-checkbox', () => {
            this.handle_selection_lock(listview);
        });
    },

    refresh(listview) {
        this.style_columns(listview);
        this.handle_selection_lock(listview);
        this.add_custom_buttons(listview);
    },
    
    add_custom_buttons(listview) {
        const allowed_roles = ['Dispatch', 'Dispatcher', 'Administrator', 'System Manager', 'Manager', 'President'];
        const has_role = allowed_roles.some(role => frappe.user_roles.includes(role));
        
        if (has_role) {
            // Remove existing to avoid duplicates on refresh
            listview.page.remove_action_item('Create Trip Ticket');
            
            listview.page.add_action_item('Create Trip Ticket', () => {
                const selected = listview.get_checked_items();
                if (!selected || selected.length === 0) {
                    frappe.msgprint('Please select at least one Sales record.');
                    return;
                }
                
                let invalid = selected.filter(d => d.status !== 'Pending');
                if (invalid.length > 0) {
                    frappe.msgprint('Only Pending Sales records can be added to a Trip Ticket.');
                    return;
                }
                
                let invalidPickups = selected.filter(d => d.fulfillment_type === 'Pick-up');
                if (invalidPickups.length > 0) {
                    frappe.msgprint('Pick-up orders cannot be added to a Trip Ticket.');
                    return;
                }
                
                let customer = selected[0].customer_link;
                let address = selected[0].address;
                
                frappe.model.with_doctype('Trip Ticket', function() {
                    let tt = frappe.model.get_new_doc('Trip Ticket');
                    tt.outlet = customer;
                    tt.address = address;
                    
                    selected.forEach(s => {
                        let row = frappe.model.add_child(tt, 'table_cpme');
                        row.sales_no = s.name;
                        row.order_no = s.order_ref;
                    });
                    
                    frappe.set_route('Form', 'Trip Ticket', tt.name);
                });
            });
        }
    },
    
    handle_selection_lock(listview) {
        setTimeout(() => {
            const selected = listview.get_checked_items();
            listview.$result.find('.list-row-checkbox').prop('disabled', false).attr('title', '');
            listview.$result.find('.list-row').removeClass('row-locked');
            
            if ($('#selection-hint-msg').length === 0) {
                listview.$result.before('<div id="selection-hint-msg" style="display:none; padding: 10px; margin-bottom: 10px; background-color: #fcf8e3; border: 1px solid #faebcc; color: #8a6d3b; border-radius: 4px;">Only Pending Sales records with the <b>same customer</b> and <b>delivery address</b> can be bundled.</div>');
            }
            
            if (selected.length > 0) {
                const customer = selected[0].customer_link;
                const address = selected[0].address;
                let lockedCount = 0;
                
                listview.data.forEach(d => {
                    if (!d.name) return;
                    const isMismatched = (d.customer_link !== customer || d.address !== address);
                    const notPending = (d.status !== 'Pending');
                    const isPickup = (d.fulfillment_type === 'Pick-up');
                    
                    if (isMismatched || notPending || isPickup) {
                        const $checkbox = listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`);
                        if ($checkbox.length && !$checkbox.prop('checked')) {
                            $checkbox.prop('disabled', true);
                            let reason = isPickup ? 'Pick-up orders skip Dispatching.' : (notPending ? 'Only Pending records allowed.' : 'Mismatched address.');
                            $checkbox.attr('title', reason);
                            $checkbox.closest('.list-row').addClass('row-locked');
                            if (isMismatched) lockedCount++;
                        }
                    }
                });
                
                if (lockedCount > 0) $('#selection-hint-msg').slideDown(200);
                else $('#selection-hint-msg').slideUp(200);
            } else {
                listview.data.forEach(d => {
                    if (d.status !== 'Pending' || d.fulfillment_type === 'Pick-up') {
                        const $checkbox = listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`);
                        if ($checkbox.length && !$checkbox.prop('checked')) {
                            $checkbox.prop('disabled', true);
                        }
                    }
                });
                $('#selection-hint-msg').slideUp(200);
            }
        }, 100);
    },

    inject_css() {
        if (document.getElementById('sales-list-css')) return;
        const style = document.createElement('style');
        style.id = 'sales-list-css';
        style.textContent = `
            #page-List\\/Sales\\/List .list-subject { flex: 0 0 140px !important; min-width: 140px !important; max-width: 140px !important; font-weight: bold; }
            #page-List\\/Sales\\/List .sales-col-status { flex: 0 0 130px !important; min-width: 130px !important; display: flex !important; align-items: center; }
            #page-List\\/Sales\\/List .sales-col-customer { flex: 0 0 200px !important; min-width: 200px !important; }
            #page-List\\/Sales\\/List .sales-col-address { flex: 0 0 200px !important; min-width: 200px !important; }
            #page-List\\/Sales\\/List .sales-col-total { flex: 0 0 120px !important; min-width: 120px !important; text-align: right; }
            #page-List\\/Sales\\/List .sales-col-order { flex: 0 0 140px !important; min-width: 140px !important; }
            #page-List\\/Sales\\/List .sales-col-date { flex: 0 0 120px !important; min-width: 120px !important; }
            #page-List\\/Sales\\/List .list-row-head, #page-List\\/Sales\\/List .list-row-container .list-row { min-width: 1050px !important; display: flex !important; flex-wrap: nowrap !important; }
            #page-List\\/Sales\\/List .result { overflow-x: auto !important; }
            #page-List\\/Sales\\/List .list-row-head .list-subject .level-item { display: none !important; }
            #page-List\\/Sales\\/List .list-row-head .list-subject:after { content: "ID"; font-weight: bold; padding-left: 10px; }
            .row-locked { opacity: 0.6; background-color: #f9f9f9 !important; }
        `;
        document.head.appendChild(style);
    },

    style_columns(listview) {
        const page = listview.page.wrapper[0];
        const fieldClassMap = { 'status': 'sales-col-status', 'customer_link': 'sales-col-customer', 'address': 'sales-col-address', 'grand_total': 'sales-col-total', 'order_ref': 'sales-col-order', 'creation_date': 'sales-col-date' };
        $(page).find('.list-row-head .list-row-col, .list-row-container .list-row .list-row-col').each(function() {
            const $col = $(this);
            const $filter = $col.find('[data-filter]');
            if ($filter.length) {
                const field = $filter.attr('data-filter').split(',')[0];
                if (fieldClassMap[field]) $col.addClass(fieldClassMap[field]);
            } else {
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

# Rename existing script or create new
roqson.update_doc("Client Script", "Sales: Paid Validation", {"name": "Sales: Master Script", "script": new_sales_list_script})
print("Updated and renamed script to Sales: Master Script")
