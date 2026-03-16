import roqson
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')

list_script = """
// -- Sales List View Script ---------------------------------------------------
// Bulletproof alignment, banner restoration, and trip ticket fix

const SL_WIDTHS = {
    "check":    "45px",
    "id":       "160px",
    "status":   "130px",
    "customer": "300px",
    "address":  "450px",
    "total":    "140px",
    "order":    "150px",
    "date":     "130px",
};
const SL_TOTAL_WIDTH = "1700px";

function sl_apply_styles(listview) {
    const page = listview.page.wrapper[0];
    if (!page) return;

    // Helper to set identical properties
    const styleCell = (el, w, align = 'left') => {
        $(el).css({
            "flex": `0 0 ${w}`,
            "min-width": w,
            "max-width": w,
            "padding": "0 12px",
            "display": "flex",
            "align-items": "center",
            "justify-content": align === 'right' ? 'flex-end' : (align === 'center' ? 'center' : 'flex-start'),
            "overflow": "visible",
            "white-space": "nowrap",
            "box-sizing": "border-box"
        });
    };

    // 1. Force overall row container widths
    $(page).find(".list-row-head, .list-row").css({
        "min-width": SL_TOTAL_WIDTH,
        "display": "flex",
        "flex-wrap": "nowrap",
        "width": "max-content"
    });

    // 2. Align Header
    const $head = $(page).find(".list-row-head");
    styleCell($head.find(".list-subject"), SL_WIDTHS.check);
    
    $head.find(".list-row-col").each(function() {
        const txt = $(this).text().trim().toLowerCase();
        if (txt === "tag") {
            $(this).css("display", "none !important").hide();
            return;
        }
        
        let w = "120px";
        let align = "left";
        
        if (txt === "id") w = SL_WIDTHS.id;
        else if (txt === "status") { w = SL_WIDTHS.status; align = "center"; }
        else if (txt === "customer") w = SL_WIDTHS.customer;
        else if (txt === "address") w = SL_WIDTHS.address;
        else if (txt === "grand total") { w = SL_WIDTHS.total; align = "right"; }
        else if (txt.includes("ref")) w = SL_WIDTHS.order;
        else if (txt.includes("date") || txt.includes("creation")) w = SL_WIDTHS.date;
        
        styleCell(this, w, align);
    });

    // 3. Align Rows
    $(page).find(".list-row-container .list-row").each(function() {
        const $row = $(this);
        
        // Subject (Checkbox)
        styleCell($row.find(".list-subject"), SL_WIDTHS.check);
        $row.find(".list-subject .level-item.ellipsis").hide(); // Hide the "-" link if it's there
        
        // Data Columns
        $row.find(".list-row-col").each(function() {
            const $col = $(this);
            
            // Hide Tags
            if ($col.hasClass("tag-col")) {
                $col.css("display", "none !important").hide();
                return;
            }

            const $filter = $col.find("[data-filter]");
            if ($filter.length) {
                const field = ($filter.attr("data-filter") || "").split(",")[0];
                let w = "120px";
                let align = "left";
                
                if (field === "name") w = SL_WIDTHS.id;
                else if (field === "status") { w = SL_WIDTHS.status; align = "center"; }
                else if (field === "customer_link") w = SL_WIDTHS.customer;
                else if (field === "address") w = SL_WIDTHS.address;
                else if (field === "grand_total") { w = SL_WIDTHS.total; align = "right"; }
                else if (field === "order_ref") w = SL_WIDTHS.order;
                else if (field === "creation_date") w = SL_WIDTHS.date;
                
                styleCell(this, w, align);
            }
        });
    });
}

frappe.listview_settings["Sales"] = {
    add_fields: ["status", "customer_link", "address", "grand_total", "order_ref", "creation_date", "fulfillment_type", "contact_number", "contact_person"],

    formatters: {
        status: function(value) {
            const colors = {
                "Pending":     { bg: "#FEFCE8", text: "#854D0E", border: "rgba(133, 77, 14, 0.15)" },
                "Dispatching": { bg: "#F0FDFA", text: "#134E4A", border: "rgba(19, 78, 74, 0.15)" },
                "In Transit":  { bg: "#EFF6FF", text: "#1E40AF", border: "rgba(30, 64, 175, 0.15)" },
                "Received":    { bg: "#F0FDF4", text: "#166534", border: "rgba(22, 101, 52, 0.15)" },
                "Failed":      { bg: "#FEF2F2", text: "#991B1B", border: "rgba(153, 27, 27, 0.15)" },
                "Completed":   { bg: "#ECFDF5", text: "#065F46", border: "rgba(6, 95, 70, 0.15)" },
                "Cancelled":   { bg: "#FFF1F2", text: "#9F1239", border: "rgba(159, 18, 57, 0.15)" },
            }[value];
            if (!colors) return value;
            const s = `background-color:${colors.bg};color:${colors.text};border:1px solid ${colors.border};border-radius:9999px;padding:2px 10px;font-size:11px;font-weight:600;white-space:nowrap;display:inline-block;line-height:1.4;`;
            return `<span style="${s}">${value}</span>`;
        }
    },

    onload: function(listview) {
        // Clear filters
        setTimeout(() => { if (listview.filter_area) listview.filter_area.clear(); }, 200);

        // Inject Base CSS
        if (!document.getElementById("sl-base-css")) {
            const el = document.createElement("style");
            el.id = "sl-base-css";
            el.textContent = `
                #page-List\\/Sales\\/List .list-row-activity, 
                #page-List\\/Sales\\/List .list-header-meta,
                #page-List\\/Sales\\/List .tag-col { display:none !important; }
                #page-List\\/Sales\\/List .result { overflow-x:auto !important; padding-bottom: 40px !important; }
                #page-List\\/Sales\\/List .layout-main-section { overflow: visible !important; }
                .row-locked { opacity: 0.4; background-color: #f8f9fa !important; pointer-events: none; }
                #selection-hint-msg { 
                    margin-bottom: 15px; padding: 12px 16px; background: #fff9db; 
                    border: 1px solid #ffec99; color: #856404; border-radius: 8px; 
                    font-weight: 600; display: flex; align-items: center; gap: 8px;
                }
            `;
            document.head.appendChild(el);
        }
        
        listview.$result.on('change', '.list-row-checkbox', () => this.handle_selection_lock(listview));
    },

    refresh: function(listview) {
        this.add_bundle_actions(listview);
        this.handle_selection_lock(listview);
        setTimeout(() => { sl_apply_styles(listview); }, 300);
        setTimeout(() => { sl_apply_styles(listview); }, 800);
    },

    add_bundle_actions: function(listview) {
        const roles = ["Dispatch", "Dispatcher", "Administrator", "System Manager", "Manager", "President"];
        if (roles.some(r => frappe.user_roles.includes(r))) {
            listview.page.remove_actions_menu_item("Create Trip Ticket");
            listview.page.add_actions_menu_item("Create Trip Ticket", () => {
                const selected = listview.get_checked_items();
                if (!selected.length) return;
                
                // Fetch full details from first record
                frappe.db.get_doc("Sales", selected[0].name).then(sales_doc => {
                    frappe.model.with_doctype("Trip Ticket", () => {
                        const tt = frappe.model.get_new_doc("Trip Ticket");
                        tt.outlet = sales_doc.customer_link;
                        tt.address = sales_doc.address;
                        tt.contact_number = sales_doc.contact_number;
                        tt.contact_person = sales_doc.contact_person;
                        
                        selected.forEach(s => {
                            const row = frappe.model.add_child(tt, "table_cpme");
                            row.sales_no = s.name;
                            row.order_no = s.order_ref;
                        });
                        frappe.set_route("Form", "Trip Ticket", tt.name);
                    });
                });
            });
        }
    },

    handle_selection_lock: function(listview) {
        const selected = listview.get_checked_items();
        
        // Restore Banner
        if ($('#selection-hint-msg').length === 0) {
            listview.$result.before('<div id="selection-hint-msg" style="display:none;"><i class="fa fa-info-circle"></i> Only Pending Sales records with the same customer and delivery address can be bundled.</div>');
        }

        if (selected.length > 0) {
            $('#selection-hint-msg').slideDown(200);
            const { customer_link: cust, address: addr } = selected[0];
            
            listview.data.forEach(d => {
                if (!d.name) return;
                const isMatch = (d.customer_link === cust && d.address === addr && d.status === "Pending" && d.fulfillment_type !== "Pick-up");
                if (!isMatch) {
                    const $cb = listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`);
                    if ($cb.length && !$cb.prop("checked")) {
                        $cb.prop("disabled", true).closest(".list-row").addClass("row-locked");
                    }
                }
            });
        } else {
            $('#selection-hint-msg').slideUp(200);
            listview.$result.find(".list-row-checkbox").prop("disabled", false);
            listview.$result.find(".list-row").removeClass("row-locked");
            
            // Still disable non-Pending or Pick-ups
            listview.data.forEach(d => {
                if (d.status !== "Pending" || d.fulfillment_type === "Pick-up") {
                    listview.$result.find(`.list-row-checkbox[data-name="${d.name}"]`).prop("disabled", true);
                }
            });
        }
    }
};
"""

roqson.update_doc("Client Script", "Sales List Script", {"script": list_script})
print("Applied alignment fix, restored banner, and fixed trip ticket detail mapping.")
