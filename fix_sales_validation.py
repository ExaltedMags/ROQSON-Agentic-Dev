import roqson

script_name = "Sales: Form Logic & Calculations"
old_script = roqson.get_script_body("Client Script", script_name)

new_script = """// DocType: Sales
// Logic for table calculations and footer rendering to mimic Order Form

frappe.ui.form.on('Sales', {
    setup(frm) {
        // Validation for required fields handled mostly server-side or allowed to pass
        // since Sales table is a read-only mirror of Order Form items for standard users.
    },

    refresh(frm) {
        recompute_sales_totals(frm);
        render_sales_totals_row(frm);
        
        if (frm.fields_dict.items && frm.fields_dict.items.grid) {
            let grid = frm.fields_dict.items.grid;
            
            // Enforce read-only behavior on the grid structure to prevent data tampering
            grid.cannot_add_rows = true;
            grid.cannot_delete_rows = true;
            
            const all_fields = ['item', 'qty', 'unit', 'unit_price', 'total', 'warehouse', 'is_promo', 'is_unreserved'];
            all_fields.forEach(f => {
                grid.update_docfield_property(f, 'read_only', 1);
                grid.update_docfield_property(f, 'reqd', 0); // Remove required constraints to prevent save blocking
            });
            
            // Reset custom buttons to prevent duplicates across refreshes
            grid.custom_buttons = {};
            
            // Only allow Unreserve toggling on Pending or Failed Sales
            if (frm.doc.status === 'Pending' || frm.doc.status === 'Failed') {
                grid.add_custom_button(__('Toggle Unreserve Selected'), () => {
                    const selected = grid.get_selected_children();
                    if (!selected || selected.length === 0) {
                        frappe.msgprint(__('Please select at least one row to unreserve/reserve.'));
                        return;
                    }
                    
                    let changed = false;
                    selected.forEach(row => {
                        const current_val = row.is_unreserved || 0;
                        frappe.model.set_value(row.doctype, row.name, 'is_unreserved', current_val ? 0 : 1);
                        changed = true;
                    });
                    
                    if (changed) {
                        frm.refresh_field('items');
                        frappe.show_alert({ message: __('Reserve status toggled for selected items. Please SAVE the document to apply changes.'), indicator: 'orange' });
                    }
                });
            }
            
            grid.refresh();
        }
    },

    validate(frm) {
        recompute_sales_totals(frm);
    },

    items_add(frm) {
        recompute_sales_totals(frm);
    },

    items_remove(frm) {
        recompute_sales_totals(frm);
    }
});

frappe.ui.form.on('Sales Items Table', {
    qty(frm, cdt, cdn) {
        calculate_sales_row_total(frm, cdt, cdn);
        recompute_sales_totals(frm);
    },
    unit_price(frm, cdt, cdn) {
        calculate_sales_row_total(frm, cdt, cdn);
        recompute_sales_totals(frm);
    },
    item(frm, cdt, cdn) {
        setTimeout(() => {
            calculate_sales_row_total(frm, cdt, cdn);
            recompute_sales_totals(frm);
        }, 800);
    }
});

function calculate_sales_row_total(frm, cdt, cdn) {
    let row = locals[cdt][cdn];
    let total = flt(row.qty || 0) * flt(row.unit_price || 0);
    if (isNaN(total)) total = 0;
    if (flt(row.total) !== total) {
        frappe.model.set_value(cdt, cdn, 'total', total);
    }
}

function recompute_sales_totals(frm) {
    let subtotal = 0;
    let total_qty = 0;

    (frm.doc.items || []).forEach(row => {
        let row_total = flt(row.qty || 0) * flt(row.unit_price || 0);
        if (isNaN(row_total)) row_total = 0;
        if (flt(row.total) !== row_total) {
            row.total = row_total;
        }
        subtotal += row.total;
        total_qty += flt(row.qty || 0);
    });

    let vat_amount = +(subtotal * 0.12).toFixed(2);
    let grand_total = +(subtotal + vat_amount).toFixed(2);
    
    if (isNaN(grand_total)) grand_total = 0;

    // Store calculations in frm.__totals for the footer renderer
    frm.__totals = {
        subtotal: subtotal,
        total_qty: total_qty,
        vat_amount: vat_amount,
        grand_total: grand_total
    };

    // Update grand_total field if it exists
    if (frm.fields_dict.grand_total) {
        frm.set_value('grand_total', grand_total);
    }

    render_sales_totals_row(frm);
}

function render_sales_totals_row(frm) {
    setTimeout(() => {
        let grid = frm.fields_dict['items']?.grid;
        if (!grid) return;

        let wrapper = grid.wrapper;
        wrapper.find('.sales-totals-footer-row').remove();

        if (!frm.__totals) return;

        let { subtotal, total_qty, vat_amount, grand_total } = frm.__totals;

        let fmt = val => {
            let formatted = frappe.format(val, { fieldtype: 'Currency' });
            return $(formatted).text() || formatted;
        };

        let vat_row = vat_amount > 0 ? `
            <div class="grid-row">
                <div class="data-row row" style="font-size: 13px; background: var(--fg-color, #fff);">
                    <div class="row-check col"></div>
                    <div class="row-index col"></div>
                    <div class="col grid-static-col col-xs-4"></div>
                    <div class="col grid-static-col col-xs-1"></div>
                    <div class="col grid-static-col col-xs-1"></div>
                    <div class="col grid-static-col col-xs-2 text-right">
                        <div class="static-area ellipsis">VAT (12%)</div>
                    </div>
                    <div class="col grid-static-col col-xs-2 text-right">
                        <div class="static-area ellipsis">${fmt(vat_amount)}</div>
                    </div>
                    <div class="col grid-static-col"></div>
                </div>
            </div>
        ` : '';

        let grand_total_row = `
            <div class="grid-row">
                <div class="data-row row" style="font-weight: 700; font-size: 13px; background: var(--fg-color, #fff); border-top: 1px solid var(--border-color, #d1d8dd);">
                    <div class="row-check col"></div>
                    <div class="row-index col"></div>
                    <div class="col grid-static-col col-xs-4"></div>
                    <div class="col grid-static-col col-xs-1"></div>
                    <div class="col grid-static-col col-xs-1"></div>
                    <div class="col grid-static-col col-xs-2 text-right">
                        <div class="static-area ellipsis">Grand Total</div>
                    </div>
                    <div class="col grid-static-col col-xs-2 text-right">
                        <div class="static-area ellipsis">${fmt(grand_total)}</div>
                    </div>
                    <div class="col grid-static-col"></div>
                </div>
            </div>
        `;

        let footer = $(`
            <div class="sales-totals-footer-row">
                <div class="grid-row">
                    <div class="data-row row" style="
                        font-weight: 700;
                        font-size: 13px;
                        background: var(--fg-color, #fff);
                        border-top: 2px solid var(--border-color, #d1d8dd);
                    ">
                        <div class="row-check col"></div>
                        <div class="row-index col"></div>
                        <div class="col grid-static-col col-xs-4 text-right">
                            <div class="static-area ellipsis" style="padding-right: 8px;">Total Quantity</div>
                        </div>
                        <div class="col grid-static-col col-xs-1 text-right">
                            <div class="static-area ellipsis">${total_qty}</div>
                        </div>
                        <div class="col grid-static-col col-xs-1"></div>
                        <div class="col grid-static-col col-xs-2 text-right">
                            <div class="static-area ellipsis">Total</div>
                        </div>
                        <div class="col grid-static-col col-xs-2 text-right">
                            <div class="static-area ellipsis">${fmt(subtotal)}</div>
                        </div>
                        <div class="col grid-static-col"></div>
                    </div>
                </div>
                ${vat_row}
                ${grand_total_row}
            </div>
        `);

        wrapper.find('.grid-footer').after(footer);

    }, 400);
}
"""

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
