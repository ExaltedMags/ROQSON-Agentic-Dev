import roqson
import requests
import os
import json

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

# 1. Update List View Settings to ensure columns are configured correctly
try:
    lvs = roqson.get_doc("List View Settings", "Sales")
    # Make sure status and fulfillment_type are in the fields JSON
    fields = [
        {"fieldname": "name", "label": "ID"},
        {"fieldname": "status", "label": "Status"},
        {"fieldname": "customer_link", "label": "Customer"},
        {"fieldname": "address", "label": "Address"},
        {"fieldname": "grand_total", "label": "Grand Total"},
        {"fieldname": "order_ref", "label": "Order Ref."},
        {"fieldname": "creation_date", "label": "Date Created"},
        {"fieldname": "fulfillment_type", "label": "Fulfillment Type"}
    ]
    lvs["fields"] = json.dumps(fields)
    roqson.update_doc("List View Settings", "Sales", {"fields": json.dumps(fields)})
    print("Updated Sales List View Settings to explicitly show Status and Fulfillment Type.")
except Exception as e:
    print("Could not update List View Settings:", e)

# 2. Write the fixed Client Script
list_script = """
// Sales List Script - The Final Fix

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
    if (!colors) return label;
    const style = `background-color:${colors.bg};color:${colors.text};border:1px solid ${colors.border};border-radius:9999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;display:inline-block;line-height:1.4;`;
    return `<span style="${style}">${label}</span>`;
}

frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date', 'fulfillment_type'],
    
    // CRITICAL FIX: Removed get_indicator so Frappe doesn't hide the Status column!
    
    formatters: {
        status(value) {
            let colors = SALES_STATE_COLORS[value];
            return colors ? sales_badge_html(colors, value) : value;
        },
        fulfillment_type(value) {
            return `<span style="font-weight:600; color:#555;">${value || 'Delivery'}</span>`;
        }
    },
    
    onload(listview) {
        listview.page.wrapper.addClass('roqson-scrollable-list');
        
        // Remove default filters (like docstatus)
        setTimeout(() => {
            if (listview.filter_area && listview.filter_area.filter_list) {
                const filters = listview.filter_area.get();
                if (filters.length > 0 && !listview.__cleared) {
                    listview.filter_area.clear();
                    listview.__cleared = true;
                }
            }
        }, 200);

        function injectCSS() {
            const existing = document.getElementById("sales-list-css");
            if (existing) existing.remove();
            const style = document.createElement("style");
            style.id    = "sales-list-css";
            style.textContent = `
/* 1. SCROLLING AND TRUNCATION FIXES */
.roqson-scrollable-list .layout-main-section,
.roqson-scrollable-list .page-body,
.roqson-scrollable-list .frappe-list,
.roqson-scrollable-list .layout-main-section-wrapper {
    overflow: visible !important; 
}

.roqson-scrollable-list .result { 
    overflow-x: auto !important; 
    -webkit-overflow-scrolling: touch; 
    width: 100% !important;
    display: block !important;
    padding-bottom: 20px !important; /* give room for scrollbar */
}

/* Force container wide enough to trigger scroll */
.roqson-scrollable-list .list-row-head,
.roqson-scrollable-list .list-row-container .list-row {
    min-width: 1500px !important;
    width: max-content !important;
    display: flex !important;
    flex-wrap: nowrap !important;
}

/* STOP TRUNCATION EVERYWHERE */
.roqson-scrollable-list .list-row-col { 
    margin-right: 0 !important; 
    overflow: visible !important; 
    text-overflow: clip !important; 
    white-space: nowrap !important; 
    flex: 1 1 auto !important; /* let them grow */
    padding-left: 10px !important;
    padding-right: 10px !important;
}

/* SPECIFIC COLUMN MINIMUM WIDTHS USING CSS :has() */
.roqson-scrollable-list .list-row-col:has([data-filter*="name"]) { min-width: 140px !important; font-weight: bold; }
.roqson-scrollable-list .list-row-col:has([data-filter*="status"]) { min-width: 130px !important; display: flex !important; align-items: center !important; }
.roqson-scrollable-list .list-row-col:has([data-filter*="customer"]) { min-width: 250px !important; }
/* The address column - very wide */
.roqson-scrollable-list .list-row-col:has([data-filter*="address"]) { min-width: 400px !important; }
.roqson-scrollable-list .list-row-col:has([data-filter*="order_ref"]) { min-width: 140px !important; }
.roqson-scrollable-list .list-row-col:has([data-filter*="grand_total"]) { min-width: 130px !important; }
.roqson-scrollable-list .list-row-col:has([data-filter*="fulfillment_type"]) { min-width: 140px !important; }

/* Remove junk icons */
.roqson-scrollable-list .list-row-activity .comment-count,
.roqson-scrollable-list .list-row-activity .mx-2,
.roqson-scrollable-list .list-row-activity .list-row-like,
.roqson-scrollable-list .list-header-meta .list-liked-by-me,
.roqson-scrollable-list .list-subject .level-item.bold,
.roqson-scrollable-list .list-subject .level-item.ellipsis,
.roqson-scrollable-list .list-header-subject .list-subject-title,
.roqson-scrollable-list .list-header-subject .list-header-meta { 
    display: none !important; 
}

.roqson-scrollable-list .list-subject {
    flex: 0 0 auto !important; 
    min-width: 30px !important; 
}

/* Prevent Frappe from hiding columns on smaller screens */
.roqson-scrollable-list .list-row-col.hidden-xs,
.roqson-scrollable-list .list-row-col.hidden-sm,
.roqson-scrollable-list .list-row-col.hidden-md,
.roqson-scrollable-list .list-row-head .list-row-col.hidden-xs,
.roqson-scrollable-list .list-row-head .list-row-col.hidden-sm,
.roqson-scrollable-list .list-row-head .list-row-col.hidden-md {
    display: flex !important;
}

.row-locked { opacity: 0.5; background-color: #f9f9f9 !important; pointer-events: none; }
`;
            document.head.appendChild(style);
        }

        injectCSS();
        
        if (!listview.page.fields_dict.address_filter) {
            listview.page.add_field({
                fieldname: 'address_filter', fieldtype: 'Data', label: 'Filter by Address',
                change: function() {
                    const val = this.get_value();
                    listview.filter_area.filter_list.filters.filter(f => f.fieldname === 'address').forEach(f => f.remove());
                    if (val) listview.filter_area.add([['Sales', 'address', 'like', '%' + val + '%']]);
                    listview.filter_area.filter_list.apply();
                }
            });
        }
        
        listview.$result.on('change', '.list-row-checkbox', () => this.handle_selection_lock(listview));
    },
    
    refresh(listview) {
        listview.page.wrapper.addClass('roqson-scrollable-list');
        this.handle_selection_lock(listview);
        this.add_bundle_actions(listview);
        
        // Manual fallback for column sizing if CSS :has() fails in older browsers
        setTimeout(() => {
            const page = listview.page.wrapper[0];
            const headerCols = Array.from(page.querySelectorAll('.list-row-head .list-row-col'));
            
            headerCols.forEach((hCol, idx) => {
                const text = (hCol.textContent || '').trim().toLowerCase();
                if (text.includes('address')) {
                    hCol.style.setProperty('min-width', '400px', 'important');
                    hCol.style.setProperty('white-space', 'nowrap', 'important');
                    hCol.style.setProperty('overflow', 'visible', 'important');
                    
                    const rows = page.querySelectorAll('.list-row-container .list-row');
                    rows.forEach(row => {
                        const dataCols = Array.from(row.querySelectorAll('.list-row-col'));
                        if (dataCols[idx]) {
                            dataCols[idx].style.setProperty('min-width', '400px', 'important');
                            dataCols[idx].style.setProperty('white-space', 'nowrap', 'important');
                            dataCols[idx].style.setProperty('overflow', 'visible', 'important');
                        }
                    });
                }
            });
        }, 200);
    },
    
    add_bundle_actions(listview) {
        const allowed_roles = ['Dispatch', 'Dispatcher', 'Administrator', 'System Manager', 'Manager', 'President'];
        const has_role = allowed_roles.some(role => frappe.user_roles.includes(role));
        
        if (has_role) {
            const actionFunc = () => {
                const selected = listview.get_checked_items();
                if (!selected || !selected.length) return frappe.msgprint('Select at least one Sales record.');
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
            };

            // 1. Add as an Inner Button (always visible, very reliable)
            listview.page.add_inner_button('Create Trip Ticket', actionFunc).addClass('btn-primary');
            
            // 2. Add as a Menu Item (under the ... menu)
            listview.page.add_menu_item('Create Trip Ticket', actionFunc);
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
    }
};
"""

roqson.update_doc("Client Script", "Sales List Script", {"script": list_script})
print("Updated List Script with bulletproof UI overrides.")
