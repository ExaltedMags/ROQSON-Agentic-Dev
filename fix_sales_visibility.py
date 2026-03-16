import roqson
import requests
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

list_script = """
// Sales List Script - Robust Version

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

// ── Column width definitions ──────────────────────────────────────────
const SALES_COL_WIDTHS = {
    "sales-col-id":          "140px",
    "sales-col-status":      "130px",
    "sales-col-customer":    "240px",
    "sales-col-address":     "220px",
    "sales-col-total":       "120px",
    "sales-col-order":       "140px",
    "sales-col-date":        "120px",
    "sales-col-fulfillment": "120px",
};

const SALES_ROW_WIDTH = "1350px";

function apply_sales_column_styles(listview) {
    const page = listview.page.wrapper[0];
    if (!page) return;

    const fieldClassMap = {
        "name":             "sales-col-id",
        "status":           "sales-col-status",
        "customer_link":    "sales-col-customer",
        "address":          "sales-col-address",
        "grand_total":      "sales-col-total",
        "order_ref":        "sales-col-order",
        "creation_date":    "sales-col-date",
        "fulfillment_type": "sales-col-fulfillment",
    };

    // Header logic
    $(page).find(".list-row-head .list-row-col").each(function() {
        const $col = $(this);
        const text = $col.text().trim();
        let cls = null;
        if (text === "ID") cls = "sales-col-id";
        else if (text === "Status") cls = "sales-col-status";
        else if (text === "Customer") cls = "sales-col-customer";
        else if (text === "Address") cls = "sales-col-address";
        else if (text === "Grand Total") cls = "sales-col-total";
        else if (text === "Order Ref.") cls = "sales-col-order";
        else if (text === "Date Created" || text === "Creation") cls = "sales-col-date";
        else if (text === "Fulfillment Type") cls = "sales-col-fulfillment";

        if (cls) {
            const w = SALES_COL_WIDTHS[cls];
            $col.css({
                "flex": `0 0 ${w}`,
                "min-width": w,
                "max-width": w,
                "padding-left": "8px",
                "padding-right": "8px"
            });
        }
    });

    // Data rows logic
    $(page).find(".list-row-container .list-row").each(function() {
        const $row = $(this);
        $row.find(".list-row-col").each(function() {
            const $col = $(this);
            const $filter = $col.find("[data-filter]");
            if ($filter.length) {
                const field = ($filter.attr("data-filter") || "").split(",")[0];
                const cls = fieldClassMap[field];
                if (cls) {
                    const w = SALES_COL_WIDTHS[cls];
                    $col.css({
                        "flex": `0 0 ${w}`,
                        "min-width": w,
                        "max-width": w,
                        "padding-left": "8px",
                        "padding-right": "8px",
                        "overflow": "hidden",
                        "text-overflow": "ellipsis",
                        "white-space": "nowrap"
                    });
                    if (cls === "sales-col-status") {
                        $col.css({ "display": "flex", "align-items": "center" });
                    }
                }
            }
        });
        
        // Ensure Subject/ID is styled if it's not caught by data-filter
        const $sub = $row.find(".list-subject");
        if ($sub.length) {
            const w = SALES_COL_WIDTHS["sales-col-id"];
            $sub.css({
                "flex": `0 0 ${w}`,
                "min-width": w,
                "max-width": w,
                "font-weight": "bold"
            });
        }
    });
}

frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date', 'fulfillment_type'],
    
    formatters: {
        status(value) {
            let colors = SALES_STATE_COLORS[value];
            return colors ? sales_badge_html(colors, value) : value;
        }
    },
    
    onload(listview) {
        this.inject_css();
        
        if (!listview.page.fields_dict.address_filter) {
            listview.page.add_field({
                fieldname: 'address_filter', fieldtype: 'Data', label: 'Filter by Address',
                change: function() {
                    const val = this.get_value();
                    listview.filter_area.filter_list.filters.filter(f => f.fieldname === 'address').forEach(f => f.remove());
                    if (val) listview.filter_area.add([['Sales', 'address', 'like', '%' + val + '%']]);
                }
            });
        }
        
        listview.$result.on('change', '.list-row-checkbox', () => this.handle_selection_lock(listview));
        this.add_bundle_actions(listview);
    },
    
    refresh(listview) {
        this.handle_selection_lock(listview);
        this.add_bundle_actions(listview);
        
        // Style columns with a slight delay to let Frappe render
        setTimeout(() => {
            apply_sales_column_styles(listview);
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
            } else {
                listview.data.forEach(d => {
                    if (d.status !== 'Pending' || d.fulfillment_type === 'Pick-up') {
                        listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`).prop('disabled', true);
                    }
                });
            }
        }, 100);
    },
    
    inject_css() {
        if (document.getElementById('sales-list-css')) return;
        const style = document.createElement('style');
        style.id = 'sales-list-css';
        style.textContent = `
            #page-List\\/Sales\\/List .list-row-head, #page-List\\/Sales\\/List .list-row-container .list-row { 
                min-width: ${SALES_ROW_WIDTH} !important; 
                flex-wrap: nowrap !important; 
                display: flex !important; 
            }
            #page-List\\/Sales\\/List .result { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }
            #page-List\\/Sales\\/List .list-row-col { margin-right: 0 !important; }
            .row-locked { opacity: 0.5; background-color: #f9f9f9 !important; }
            
            /* Ensure activity and tags don't break the flow */
            #page-List\\/Sales\\/List .list-row-activity, #page-List\\/Sales\\/List .list-row-head .level-right {
                flex: 0 0 100px !important;
                min-width: 100px !important;
            }
        `;
        document.head.appendChild(style);
    }
};
"""

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
    print("Updated List Script with robust horizontal scrolling.")
except Exception as e:
    print("Error:", e)
