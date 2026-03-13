import roqson
import requests
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

form_script = """
// Sales Form Script

frappe.ui.form.on('Sales', {
    status: function(frm) {
        if (frm.doc.status === 'Completed' && !frm.is_new()) {
            frappe.db.get_list('File', {
                filters: { attached_to_doctype: 'Sales', attached_to_name: frm.doc.name },
                fields: ['name'], limit: 1
            }).then(files => {
                if (!files || !files.length) {
                    frappe.msgprint({ title: 'Receipt Required', message: 'Attach a receipt before marking Completed.', indicator: 'red' });
                    frappe.model.set_value(frm.doctype, frm.docname, 'status', 'Pending');
                }
            });
        }
    },
    refresh(frm) {
        const roles = frappe.user_roles;
        const can_confirm = roles.includes('Administrator') || roles.includes('System Manager') || roles.includes('Warehouse') || roles.includes('Manager');
        if (frm.doc.fulfillment_type === 'Pick-up' && frm.doc.status === 'Pending' && can_confirm) {
            frm.page.add_inner_button('Confirm Pick-up', () => {
                frappe.confirm('Has the customer collected these items?', () => {
                    frm.set_value('status', 'Received');
                    frm.save();
                });
            }).addClass('btn-primary').css({'color': 'white', 'background-color': '#166534'});
        }
    },
    before_save: function(frm) {
        if (frm.doc.status === 'Completed' && !frm.is_new()) {
            return new Promise((resolve, reject) => {
                frappe.db.get_list('File', {
                    filters: { attached_to_doctype: 'Sales', attached_to_name: frm.doc.name },
                    fields: ['name'], limit: 1
                }).then(files => {
                    if (!files || !files.length) {
                        frappe.msgprint({ title: 'Receipt Required', message: 'Cannot save as Completed: no receipt files attached.', indicator: 'red' });
                        reject('No receipt attached');
                    } else {
                        resolve();
                    }
                });
            });
        }
    }
});
"""

list_script = """
// Sales List Script

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
    const style = `background-color:${colors.bg};color:${colors.text};border:1px solid ${colors.border};border-radius:9999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;display:inline-block;line-height:1.4;`;
    return `<span style="${style}">${label}</span>`;
}

frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date', 'fulfillment_type'],
    
    get_indicator: function(doc) {
        const map = { 'Pending': ['orange'], 'Dispatching': ['cyan'], 'In Transit': ['blue'], 'Received': ['green'], 'Failed': ['red'], 'Completed': ['emerald'], 'Cancelled': ['grey'] };
        return [doc.status, map[doc.status] || 'grey', `status,=,${doc.status}`];
    },
    
    formatters: {
        status(value) {
            let colors = SALES_STATE_COLORS[value];
            return colors ? sales_badge_html(colors, value) : value;
        }
    },
    
    onload(listview) {
        this.inject_css();
        listview.page.add_field({
            fieldname: 'address_filter', fieldtype: 'Data', label: 'Filter by Address',
            change: function() {
                const val = this.get_value();
                listview.filter_area.filter_list.filters.filter(f => f.fieldname === 'address').forEach(f => f.remove());
                if (val) listview.filter_area.add([['Sales', 'address', 'like', '%' + val + '%']]);
            }
        });
        
        listview.$result.on('change', '.list-row-checkbox', () => this.handle_selection_lock(listview));
    },
    
    refresh(listview) {
        this.style_columns(listview);
        this.handle_selection_lock(listview);
        this.add_bundle_actions(listview);
    },
    
    add_bundle_actions(listview) {
        const allowed_roles = ['Dispatch', 'Dispatcher', 'Administrator', 'System Manager', 'Manager', 'President'];
        const has_role = allowed_roles.some(role => frappe.user_roles.includes(role));
        
        if (has_role) {
            listview.page.remove_action_item('Create Trip Ticket');
            listview.page.add_action_item('Create Trip Ticket', () => {
                const selected = listview.get_checked_items();
                if (!selected.length) return frappe.msgprint('Select at least one Sales record.');
                if (selected.some(d => d.status !== 'Pending')) return frappe.msgprint('Only Pending Sales records allowed.');
                if (selected.some(d => d.fulfillment_type === 'Pick-up')) return frappe.msgprint('Pick-up orders skip Trip Tickets.');
                
                frappe.model.with_doctype('Trip Ticket', () => {
                    let tt = frappe.model.get_new_doc('Trip Ticket');
                    tt.outlet = selected[0].customer_link;
                    tt.address = selected[0].address;
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
            listview.$result.find('.list-row-checkbox').prop('disabled', false);
            listview.$result.find('.list-row').removeClass('row-locked');
            
            if ($('#selection-hint-msg').length === 0) {
                listview.$result.before('<div id="selection-hint-msg" style="display:none; padding: 10px; margin-bottom: 10px; background-color: #fcf8e3; border: 1px solid #faebcc; color: #8a6d3b; border-radius: 4px;">Only Pending Sales records with the <b>same customer</b> and <b>delivery address</b> can be bundled.</div>');
            }
            
            if (selected.length > 0) {
                const { customer_link: cust, address: addr } = selected[0];
                listview.data.forEach(d => {
                    if (!d.name) return;
                    if (d.customer_link !== cust || d.address !== addr || d.status !== 'Pending' || d.fulfillment_type === 'Pick-up') {
                        const $cb = listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`);
                        if ($cb.length && !$cb.prop('checked')) {
                            $cb.prop('disabled', true).closest('.list-row').addClass('row-locked');
                        }
                    }
                });
                $('#selection-hint-msg').slideDown(200);
            } else {
                listview.data.forEach(d => {
                    if (d.status !== 'Pending' || d.fulfillment_type === 'Pick-up') {
                        listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`).prop('disabled', true);
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
            #page-List\\/Sales\\/List .list-subject { flex: 0 0 140px !important; min-width: 140px !important; font-weight: bold; }
            #page-List\\/Sales\\/List .sales-col-status { flex: 0 0 130px !important; min-width: 130px !important; display: flex !important; align-items: center; }
            #page-List\\/Sales\\/List .list-row-head, #page-List\\/Sales\\/List .list-row-container .list-row { min-width: 1050px !important; display: flex !important; flex-wrap: nowrap !important; }
            #page-List\\/Sales\\/List .result { overflow-x: auto !important; }
            #page-List\\/Sales\\/List .list-row-head .list-subject .level-item { display: none !important; }
            #page-List\\/Sales\\/List .list-row-head .list-subject:after { content: "ID"; font-weight: bold; padding-left: 10px; }
            .row-locked { opacity: 0.5; background-color: #f9f9f9 !important; }
        `;
        document.head.appendChild(style);
    },
    
    style_columns(listview) {
        const fieldClassMap = { 'status': 'sales-col-status', 'customer_link': 'sales-col-customer', 'address': 'sales-col-address', 'grand_total': 'sales-col-total', 'order_ref': 'sales-col-order', 'creation_date': 'sales-col-date' };
        $(listview.page.wrapper[0]).find('.list-row-head .list-row-col, .list-row-container .list-row .list-row-col').each(function() {
            const $col = $(this);
            const $filter = $col.find('[data-filter]');
            if ($filter.length) {
                const field = $filter.attr('data-filter').split(',')[0];
                if (fieldClassMap[field]) $col.addClass(fieldClassMap[field]);
            }
        });
    }
};
"""

# Update Form Script
print("Updating Form Script...")
roqson.update_doc("Client Script", "Sales: Paid Validation", {
    "script": form_script,
    "view": "Form"  # Ensure it's Form
})
print("Form Script updated.")

# Create/Update List Script
print("Creating/Updating List Script...")
doc_list = {
    "doctype": "Client Script",
    "name": "Sales List Script",
    "dt": "Sales",
    "view": "List",
    "script": list_script,
    "enabled": 1
}

try:
    roqson.update_doc("Client Script", "Sales List Script", doc_list)
    print("Updated existing List Script.")
except Exception:
    r = requests.post(f"{BASE_URL}/api/resource/Client Script", json=doc_list, headers=headers)
    print("Created new List Script:", r.status_code)
