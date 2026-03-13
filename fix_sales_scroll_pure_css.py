import roqson
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

list_script = """
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
        // Tag the wrapper immediately so we can target it purely with CSS
        listview.page.wrapper.addClass('custom-sales-list');

        // Clear default auto-applied filters (like docstatus)
        setTimeout(() => {
            if (listview.filter_area && listview.filter_area.filter_list) {
                const filters = listview.filter_area.get();
                if (filters.length > 0 && !listview.__user_cleared_filters) {
                    listview.filter_area.clear();
                    listview.__user_cleared_filters = true;
                }
            }
        }, 500);

        function injectCSS() {
            const existing = document.getElementById("sales-list-css");
            if (existing) existing.remove();
            const style = document.createElement("style");
            style.id    = "sales-list-css";
            style.textContent = `
/* Hide unwanted icons/meta */
.custom-sales-list .list-row-activity .comment-count,
.custom-sales-list .list-row-activity .mx-2,
.custom-sales-list .list-row-activity .list-row-like,
.custom-sales-list .list-header-meta .list-liked-by-me,
.custom-sales-list .list-subject .level-item.bold,
.custom-sales-list .list-subject .level-item.ellipsis,
.custom-sales-list .list-header-subject .list-subject-title,
.custom-sales-list .list-header-subject .list-header-meta { 
    display: none !important; 
}

.custom-sales-list .list-subject {
    flex: 0 0 auto !important; 
    min-width: 30px !important; 
    max-width: none !important;
    overflow: visible !important;
}

/* HORIZONTAL SCROLLING RULES */
.custom-sales-list .layout-main-section,
.custom-sales-list .page-body,
.custom-sales-list .frappe-list,
.custom-sales-list .layout-main-section-wrapper {
    overflow: visible !important; 
}

.custom-sales-list .result { 
    overflow-x: auto !important; 
    -webkit-overflow-scrolling: touch; 
    width: 100% !important;
    display: block !important;
}

/* Force container wide enough to trigger scroll */
.custom-sales-list .list-row-head,
.custom-sales-list .list-row-container .list-row {
    min-width: max-content !important;
    width: 100% !important;
    display: flex !important;
    flex-wrap: nowrap !important;
}

/* Base style for all columns to prevent truncation */
.custom-sales-list .list-row-col { 
    margin-right: 0 !important; 
    overflow: visible !important; 
    text-overflow: clip !important; 
    white-space: nowrap !important; 
    flex: 0 0 auto !important;
    padding-left: 8px !important;
    padding-right: 8px !important;
    min-width: 120px !important;
}

/* Prevent Frappe from hiding columns on smaller screens */
.custom-sales-list .list-row-col.hidden-xs,
.custom-sales-list .list-row-col.hidden-sm,
.custom-sales-list .list-row-col.hidden-md,
.custom-sales-list .list-row-head .list-row-col.hidden-xs,
.custom-sales-list .list-row-head .list-row-col.hidden-sm,
.custom-sales-list .list-row-head .list-row-col.hidden-md {
    display: flex !important;
}

/* TARGETED COLUMN WIDTHS USING :has() */
.custom-sales-list .list-row-col:has([data-filter*="name"]) { min-width: 150px !important; font-weight: bold; }
.custom-sales-list .list-row-col:has([data-filter*="status"]) { min-width: 130px !important; display: flex !important; align-items: center !important; }
.custom-sales-list .list-row-col:has([data-filter*="customer"]) { min-width: 260px !important; }
.custom-sales-list .list-row-col:has([data-filter*="address"]) { min-width: 350px !important; }
.custom-sales-list .list-row-col:has([data-filter*="order_ref"]) { min-width: 140px !important; }

/* Fallbacks if data-filter is missing (targets header text) */
.custom-sales-list .list-row-head .list-row-col {
    display: flex !important;
    align-items: center !important;
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
        this.add_bundle_actions(listview);
    },
    
    refresh(listview) {
        listview.page.wrapper.addClass('custom-sales-list');
        this.handle_selection_lock(listview);
        this.add_bundle_actions(listview);
        
        // Find columns without data-filter and add explicit classes based on text content
        // This makes sure columns get sized even if :has() selector doesn't catch them.
        setTimeout(() => {
            const page = listview.page.wrapper[0];
            const headerCols = Array.from(page.querySelectorAll('.list-row-head .list-row-col'));
            
            headerCols.forEach((hCol, idx) => {
                const text = (hCol.textContent || '').trim().toLowerCase();
                let width = '120px';
                
                if (text.includes('id')) width = '150px';
                else if (text.includes('status')) width = '130px';
                else if (text.includes('customer')) width = '260px';
                else if (text.includes('address')) width = '350px';
                else if (text.includes('ref')) width = '140px';
                
                hCol.style.setProperty('min-width', width, 'important');
                
                // Apply to corresponding data columns
                const rows = page.querySelectorAll('.list-row-container .list-row');
                rows.forEach(row => {
                    const dataCols = Array.from(row.querySelectorAll('.list-row-col'));
                    if (dataCols[idx]) {
                        dataCols[idx].style.setProperty('min-width', width, 'important');
                    }
                });
            });
            
            // Re-order ID to be immediately after Checkbox (Subject)
            const idHeader = headerCols.find(c => (c.textContent || '').trim() === 'ID');
            const subHeader = page.querySelector('.list-row-head .list-subject');
            if (idHeader && subHeader) subHeader.after(idHeader);
            
            const rows = page.querySelectorAll('.list-row-container .list-row');
            rows.forEach(row => {
                const dCols = Array.from(row.querySelectorAll('.list-row-col'));
                const idCol = dCols.find(c => {
                    const f = c.querySelector('[data-filter]');
                    return f && f.getAttribute('data-filter').startsWith('name,');
                });
                const subCol = row.querySelector('.list-subject');
                if (idCol && subCol) subCol.after(idCol);
            });
            
        }, 100);
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
    }
};
"""

roqson.update_doc("Client Script", "Sales List Script", {"script": list_script})
print("Updated List Script with pure CSS targeting and auto-filter clear.")
