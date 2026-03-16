import roqson
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')

list_script = """
// Sales List Script - The PERFECT Merge (Scroll, Align, Lock, Banner, Autofill)

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

// Minimum sensible widths, but they can grow larger
const SALES_COL_WIDTHS = {
    "sales-col-id":          "140px",
    "sales-col-status":      "130px",
    "sales-col-customer":    "260px",
    "sales-col-address":     "minmax(350px, max-content)",
    "sales-col-total":       "120px",
    "sales-col-order":       "140px",
    "sales-col-date":        "120px",
    "sales-col-fulfillment": "120px",
};

function style_all_columns(page) {
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

    function applyColWidth(col, cls) {
        const w = SALES_COL_WIDTHS[cls];
        if (!w) return;
        col.classList.add(cls);
        
        // Use CSS grid/flex rules to ensure it grows to fit content
        col.style.setProperty("flex", "0 0 auto", "important");
        if (cls === "sales-col-address" || cls === "sales-col-customer") {
            col.style.setProperty("width", "max-content", "important");
            col.style.setProperty("min-width", w.includes("minmax") ? "350px" : w, "important");
            col.style.setProperty("max-width", "none", "important");
        } else {
            col.style.setProperty("min-width", w, "important");
        }
        
        col.style.setProperty("padding-left", "8px", "important");
        col.style.setProperty("padding-right", "8px", "important");
        col.style.setProperty("box-sizing", "border-box", "important");
        
        // CRITICAL: Prevent truncation
        col.style.setProperty("white-space", "nowrap", "important");
        col.style.setProperty("overflow", "visible", "important");
        col.style.setProperty("text-overflow", "clip", "important");
        
        // Alignment
        col.style.setProperty("display", "flex", "important");
        col.style.setProperty("align-items", "center", "important");
        if (cls === "sales-col-status") {
            col.style.setProperty("justify-content", "center", "important");
        } else if (cls === "sales-col-total") {
            col.style.setProperty("justify-content", "flex-end", "important");
        } else if (cls === "sales-col-id") {
            col.style.setProperty("font-weight", "bold", "important");
        }
    }

    const headerRow = page.querySelector(".list-row-head");
    if (headerRow) {
        const allHCols = Array.from(headerRow.querySelectorAll(".list-row-col"));
        allHCols.forEach(col => {
            const text = (col.textContent || "").trim();
            if (text === "Tag") {
                col.style.setProperty("display", "none", "important");
                return;
            }
            const cls  = headerLabelMap[text];
            if (cls) applyColWidth(col, cls);
        });
        const idH = allHCols.find(c => (c.textContent || "").trim() === "ID");
        const subH = headerRow.querySelector(".list-subject");
        if (idH && subH) {
            applyColWidth(idH, "sales-col-id");
            subH.after(idH);
        }
    }

    page.querySelectorAll(".list-row-container .list-row").forEach(row => {
        const cols = Array.from(row.querySelectorAll(".list-row-col"));

        cols.forEach(col => {
            if (col.classList.contains("tag-col")) {
                col.style.setProperty("display", "none", "important");
                return;
            }
            const filterEl = col.querySelector("[data-filter]");
            if (!filterEl) return;
            const field = (filterEl.getAttribute("data-filter") || "").split(",")[0];
            const cls   = fieldClassMap[field];
            if (cls) applyColWidth(col, cls);
        });

        const idCol = cols.find(c => c.classList.contains("sales-col-id"));
        const subCol = row.querySelector(".list-subject");
        if (idCol && subCol) {
            applyColWidth(idCol, "sales-col-id");
            subCol.after(idCol);
        }
        
        if (subCol) {
            const links = subCol.querySelectorAll(".level-item.ellipsis a, .level-item.bold a");
            links.forEach(l => { if (l.textContent.trim() === "-") l.style.setProperty("display", "none", "important"); });
        }
    });
}

frappe.listview_settings['Sales'] = {
    add_fields: ['status', 'customer_link', 'address', 'grand_total', 'order_ref', 'creation_date', 'fulfillment_type'],
    
    // get_indicator removed so Status renders correctly
    
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
        // Clear default auto-applied filters
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
/* Remove junk icons */
#page-List\\/Sales\\/List .list-row-activity .comment-count,
#page-List\\/Sales\\/List .list-row-activity .mx-2,
#page-List\\/Sales\\/List .list-row-activity .list-row-like { display: none !important; }
#page-List\\/Sales\\/List .list-header-meta .list-liked-by-me { display: none !important; }        

/* Subject cleanup (Checkbox) */
#page-List\\/Sales\\/List .list-subject {
    flex: 0 0 45px !important; 
    min-width: 45px !important; 
    max-width: 45px !important;
    overflow: visible !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    padding: 0 !important;
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
    display: none !important; /* Hide activity column completely */
}

/* HORIZONTAL SCROLLING - NO TRUNCATION */

#page-List\\/Sales\\/List .layout-main-section,
#page-List\\/Sales\\/List .page-body,
#page-List\\/Sales\\/List .frappe-list,
#page-List\\/Sales\\/List .layout-main-section-wrapper {
    overflow: visible !important; 
}

#page-List\\/Sales\\/List .result { 
    overflow-x: auto !important; 
    -webkit-overflow-scrolling: touch; 
    width: 100% !important;
    display: block !important;
    padding-bottom: 30px !important;
}

#page-List\\/Sales\\/List .list-row-head,
#page-List\\/Sales\\/List .list-row-container .list-row {
    min-width: max-content !important;
    width: max-content !important;
    display: flex !important;
    flex-wrap: nowrap !important;
}

#page-List\\/Sales\\/List .list-row-col { 
    margin-right: 0 !important; 
    overflow: visible !important; 
    text-overflow: clip !important; 
    white-space: nowrap !important; 
    flex: 0 0 auto !important;
}

/* Force ALL columns visible on all screen sizes */
#page-List\\/Sales\\/List .list-row-col.hidden-xs,
#page-List\\/Sales\\/List .list-row-col.hidden-sm,
#page-List\\/Sales\\/List .list-row-col.hidden-md,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-xs,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-sm,
#page-List\\/Sales\\/List .list-row-head .list-row-col.hidden-md {
    display: flex !important;
}

.row-locked { opacity: 0.4; background-color: #f8f9fa !important; pointer-events: none; }
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
        this.handle_selection_lock(listview);
        this.add_bundle_actions(listview);
        
        const wrapper = listview.page.wrapper[0];
        if (wrapper) {
            const resultEl = wrapper.querySelector('.result');
            if (resultEl) resultEl.style.overflowX = 'auto';
        }
        
        setTimeout(() => {
            style_all_columns(wrapper);
        }, 300);
        
        setTimeout(() => {
            style_all_columns(wrapper);
        }, 800);
    },
    
    add_bundle_actions(listview) {
        const allowed_roles = ['Dispatch', 'Dispatcher', 'Administrator', 'System Manager', 'Manager', 'President'];
        const has_role = allowed_roles.some(role => frappe.user_roles.includes(role));
        
        if (has_role) {
            listview.page.remove_action_item('Create Trip Ticket');
            listview.page.remove_inner_button('Create Trip Ticket');
            
            listview.page.add_actions_menu_item('Create Trip Ticket', () => {
                const selected = listview.get_checked_items();
                if (!selected || !selected.length) return frappe.msgprint('Select at least one Sales record.');
                if (selected.some(d => d.status !== 'Pending')) return frappe.msgprint('Only Pending Sales records allowed.');
                if (selected.some(d => d.fulfillment_type === 'Pick-up')) return frappe.msgprint('Pick-up orders skip Trip Tickets.');
                
                frappe.db.get_doc("Sales", selected[0].name).then(sales_doc => {
                    frappe.model.with_doctype('Trip Ticket', () => {
                        let tt = frappe.model.get_new_doc('Trip Ticket');
                        tt.outlet = sales_doc.customer_link;
                        tt.address = sales_doc.address;
                        tt.contact_number = sales_doc.contact_number;
                        tt.contact_person = sales_doc.contact_person;
                        
                        selected.forEach(s => {
                            let row = frappe.model.add_child(tt, 'table_cpme');
                            row.sales_no = s.name;
                            row.order_no = s.order_ref;
                        });
                        frappe.set_route('Form', 'Trip Ticket', tt.name);
                    });
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
                listview.$result.before('<div id="selection-hint-msg" style="display:none; padding: 10px; margin-bottom: 10px; background-color: #fcf8e3; border: 1px solid #faebcc; color: #8a6d3b; border-radius: 4px; font-weight: 600;"><i class="fa fa-info-circle"></i> Only Pending Sales records with the same customer and delivery address can be bundled.</div>');
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
print("Applied merged logic: Perfect layout + Lock/Banner + Autofill.")
