import roqson
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

list_script = """
// Sales List Script - Robust Scroll

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
    "sales-col-address":     "300px",
    "sales-col-total":       "120px",
    "sales-col-order":       "140px",
    "sales-col-date":        "120px",
    "sales-col-fulfillment": "120px",
};

const SALES_ROW_WIDTH = "1400px";

// ── Robust column styling function ───────────────────────────────────────────
function style_all_columns(page) {
    if (!page) return;

    const SALES_CLASSES = Object.keys(SALES_COL_WIDTHS);

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

    const headerLabelMap = {
        "ID":               "sales-col-id",
        "Status":           "sales-col-status",
        "Customer":         "sales-col-customer",
        "Address":          "sales-col-address",
        "Grand Total":      "sales-col-total",
        "Order Ref.":       "sales-col-order",
        "Date Created":     "sales-col-date",
        "Creation":         "sales-col-date",
        "Fulfillment Type": "sales-col-fulfillment",
    };

    function resetCol(col) {
        col.style.cssText = "";
        SALES_CLASSES.forEach(c => col.classList.remove(c));
    }

    function applyColWidth(col, cls) {
        const w = SALES_COL_WIDTHS[cls];
        if (!w) return;
        col.classList.add(cls);
        
        const isStatus = (cls === "sales-col-status");
        if (isStatus) {
            col.setAttribute("style",
                "flex:0 0 " + w + " !important;min-width:" + w + " !important;max-width:" + w + " !important;" +
                "overflow:hidden;display:flex !important;align-items:center;padding-left:8px;padding-right:8px;box-sizing:border-box;");
        } else {
            col.setAttribute("style",
                "flex:0 0 " + w + " !important;min-width:" + w + " !important;max-width:" + w + " !important;" +
                "overflow:hidden;text-overflow:ellipsis;white-space:nowrap;padding-left:8px;padding-right:8px;box-sizing:border-box;");
        }
    }

    const headerRow = page.querySelector(".list-row-head");
    if (headerRow) {
        const allHCols = Array.from(headerRow.querySelectorAll(".list-row-col"));
        allHCols.forEach(col => {
            const text = (col.textContent || "").trim();
            const cls  = headerLabelMap[text];
            if (cls) {
                resetCol(col);
                applyColWidth(col, cls);
            }
        });
        const idH = allHCols.find(c => (c.textContent || "").trim() === "ID");
        const subH = headerRow.querySelector(".list-subject");
        if (idH && subH) {
            resetCol(idH);
            applyColWidth(idH, "sales-col-id");
            subH.after(idH);
        }
    }

    page.querySelectorAll(".list-row-container .list-row").forEach(row => {
        const cols = Array.from(row.querySelectorAll(".list-row-col"));

        cols.forEach(col => {
            if (!col.classList.contains("list-subject") && !col.classList.contains("tag-col")) {
                resetCol(col);
            }
        });

        cols.forEach(col => {
            const filterEl = col.querySelector("[data-filter]");
            if (!filterEl) return;
            const field = (filterEl.getAttribute("data-filter") || "").split(",")[0];
            const cls   = fieldClassMap[field];
            if (cls) applyColWidth(col, cls);
        });

        const idCol = cols.find(c => c.classList.contains("sales-col-id"));
        const subCol = row.querySelector(".list-subject");
        if (idCol && subCol) {
            subCol.after(idCol);
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
        function injectCSS() {
            const existing = document.getElementById("sales-list-css");
            if (existing) existing.remove();
            const style = document.createElement("style");
            style.id    = "sales-list-css";
            style.textContent = `
#page-List\\/Sales\\/List .list-row-activity .comment-count,
#page-List\\/Sales\\/List .list-row-activity .mx-2,
#page-List\\/Sales\\/List .list-row-activity .list-row-like { display: none !important; }
#page-List\\/Sales\\/List .list-header-meta .list-liked-by-me { display: none !important; }        

#page-List\\/Sales\\/List .list-subject {
    flex: 0 0 30px !important; min-width: 30px !important; max-width: 30px !important;
    overflow: hidden !important;
}
#page-List\\/Sales\\/List .list-subject .level-item.bold,
#page-List\\/Sales\\/List .list-subject .level-item.ellipsis,
#page-List\\/Sales\\/List .list-header-subject .list-subject-title,
#page-List\\/Sales\\/List .list-header-subject .list-header-meta { display: none !important; }     

#page-List\\/Sales\\/List .list-row-head .level-left,
#page-List\\/Sales\\/List .list-row-container .list-row .level-left {
    flex: 0 0 auto !important; min-width: 0 !important; max-width: none !important; overflow: visible !important;
}
#page-List\\/Sales\\/List .list-row-head .level-right,
#page-List\\/Sales\\/List .list-row-container .list-row .level-right {
    flex: 0 0 95px !important; min-width: 95px !important; max-width: 95px !important; overflow: hidden !important;
}

#page-List\\/Sales\\/List .list-row-head .level-right .list-count {
    white-space: nowrap !important; overflow: hidden !important; text-overflow: ellipsis !important;      
}

#page-List\\/Sales\\/List .list-row-col { margin-right: 0 !important; }

#page-List\\/Sales\\/List .sales-col-id {
    flex: 0 0 140px !important; min-width: 140px !important; max-width: 140px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
    font-weight: 700;
}
#page-List\\/Sales\\/List .sales-col-status {
    flex: 0 0 130px !important; min-width: 130px !important; max-width: 130px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
    display: flex !important; align-items: center !important;
}
#page-List\\/Sales\\/List .sales-col-customer {
    flex: 0 0 240px !important; min-width: 240px !important; max-width: 240px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}
#page-List\\/Sales\\/List .sales-col-address {
    flex: 0 0 300px !important; min-width: 300px !important; max-width: 300px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}
#page-List\\/Sales\\/List .sales-col-total {
    flex: 0 0 120px !important; min-width: 120px !important; max-width: 120px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}
#page-List\\/Sales\\/List .sales-col-order {
    flex: 0 0 140px !important; min-width: 140px !important; max-width: 140px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}
#page-List\\/Sales\\/List .sales-col-date {
    flex: 0 0 120px !important; min-width: 120px !important; max-width: 120px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}
#page-List\\/Sales\\/List .sales-col-fulfillment {
    flex: 0 0 120px !important; min-width: 120px !important; max-width: 120px !important;
    overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    padding-left: 8px; padding-right: 8px; box-sizing: border-box;
}

#page-List\\/Sales\\/List .list-row-activity {
    flex: 0 0 95px !important; min-width: 95px !important; max-width: 95px !important;
}

/* HORIZONTAL SCROLLING FIXES */
#page-List\\/Sales\\/List .list-row-head,
#page-List\\/Sales\\/List .list-row-container .list-row {
    min-width: 1400px !important;
    flex-wrap: nowrap !important; display: flex !important;
}

#page-List\\/Sales\\/List .layout-main-section { overflow: visible !important; }
#page-List\\/Sales\\/List .result { overflow-x: auto !important; -webkit-overflow-scrolling: touch; }

#page-List\\/Sales\\/List .list-row-col {
    overflow: hidden !important; text-overflow: ellipsis !important; white-space: nowrap !important;      
}

/* Force ALL columns visible on all screen sizes - rely on horizontal scroll instead of hiding */
#page-List\\/Sales\\/List .list-row-col.hidden-xs,
#page-List\\/Sales\\/List .list-row-col.hidden-sm,
#page-List\\/Sales\\/List .list-row-col.hidden-md,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-xs,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-sm,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-md {
    display: flex !important;
}

/* Ensure scroll container chain works on mobile/tablet */
#page-List\\/Sales\\/List .frappe-list,
#page-List\\/Sales\\/List .layout-main-section-wrapper {
    overflow: visible !important;
}
#page-List\\/Sales\\/List .result {
    overflow-x: auto !important;
    -webkit-overflow-scrolling: touch;
}

.row-locked { opacity: 0.5; background-color: #f9f9f9 !important; }
`;
            document.head.appendChild(style);
        }

        function removeCSS() {
            const el = document.getElementById("sales-list-css");
            if (el) el.remove();
        }

        injectCSS();
        if (!listview.__sales_route_handler) {
            listview.__sales_route_handler = true;
            frappe.router.on("change", () => {
                const route = frappe.get_route();
                if (route && route[0] === "List" && route[1] === "Sales") {
                    injectCSS();
                } else {
                    removeCSS();
                }
            });
        }
        
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
        
        setTimeout(() => {
            const page = document.getElementById("page-List/Sales/List");
            style_all_columns(page);
        }, 400);
        
        setTimeout(() => {
            const page = document.getElementById("page-List/Sales/List");
            style_all_columns(page);
        }, 800);
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
    print("Updated List Script with exact horizontal scroll CSS logic.")
except Exception as e:
    print("Error:", e)
