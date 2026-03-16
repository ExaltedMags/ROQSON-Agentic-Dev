import roqson

doc = roqson.get_doc("Client Script", "Order Form List - Master")
old_script = doc.get("script", "")

new_logic = """
// ── List View Workflow Interceptor (Warehouse Assignment) ─────────────────
// Injects the Warehouse Assignment popup into the List View bulk actions
// without breaking Frappe's native DOM listeners.

document.addEventListener("click", function(e) {
    if (frappe.get_route()[0] !== 'List' || frappe.get_route()[1] !== 'Order Form') return;
    
    let $target = $(e.target).closest('a.dropdown-item');
    if (!$target.length) $target = $(e.target).closest('a');
    
    if ($target.length && $target.closest('.actions-btn-group').length) {
        let action = $target.text().trim();
        if (action === 'Submit' || action === 'Approve') {
            e.preventDefault();
            e.stopPropagation();
            
            let listview = cur_list;
            let selected = listview.get_checked_items();
            if (!selected || selected.length === 0) return;
            
            (async function() {
                for (let row of selected) {
                    try {
                        frappe.dom.freeze(`Loading ${row.name}...`);
                        let doc = await frappe.db.get_doc("Order Form", row.name);
                        frappe.dom.unfreeze();
                        await new Promise((resolve, reject) => {
                            open_listview_warehouse_dialog(doc, action, listview, resolve, reject);
                        });
                    } catch (err) {
                        frappe.dom.unfreeze();
                        if (err !== 'cancelled') frappe.msgprint(String(err));
                        break; 
                    }
                }
                listview.clear_checked_items();
                listview.refresh();
            })();
        }
    }
}, true);

function open_listview_warehouse_dialog(doc, action, listview, resolve, reject) {
    const rows = doc.table_mkaq || [];
    const non_promo = rows.filter(r => !r.is_promo_reward && r.items);

    if (!non_promo.length) {
        // No items to assign, just do the workflow action
        execute_bulk_action(doc.name, action).then(resolve).catch(reject);
        return;
    }

    frappe.db.get_list('Warehouses', { fields: ['name', 'warehouse_name'], limit: 50 })
    .then(warehouses => {
        const item_codes = non_promo.map(r => r.items);
        return frappe.db.get_list('Product', {
            filters: { name: ['in', item_codes] },
            fields: ['name', 'item_description']
        }).then(products => {
            const product_map = {};
            products.forEach(p => product_map[p.name] = p.item_description || p.name);

            const wh_options = warehouses.map(w => ({ label: w.warehouse_name, value: w.name }));
            const default_wh = warehouses.length > 0 ? warehouses[0].name : '';

            const fields = [
                { fieldtype: 'Section Break', label: `Assign Warehouse - ${doc.name}` },
                {
                    fieldname: 'bulk_warehouse', fieldtype: 'Select', label: 'Set All To',
                    options: [{ label: '', value: '' }].concat(wh_options),
                    description: 'Quickly set all items to one warehouse.'
                },
                { fieldtype: 'Section Break', label: 'Per Item' }
            ];

            non_promo.forEach(function(row) {
                const desc = product_map[row.items] || row.items;
                const lbl = desc + (row.unit ? ' (' + row.unit + ', qty: ' + row.qty + ')' : ' (qty: ' + row.qty + ')');
                fields.push({
                    fieldname: 'wh_' + row.name, fieldtype: 'Select', label: lbl,
                    options: wh_options, default: row.warehouse || default_wh, reqd: 1
                });
            });

            let confirmed = false;
            const d = new frappe.ui.Dialog({
                title: action === 'Submit' ? 'Submit Order' : 'Approve Order',
                fields: fields,
                primary_action_label: 'Confirm & ' + action,
                primary_action: function(values) {
                    confirmed = true;
                    d.hide();
                    frappe.dom.freeze('Updating warehouses & applying workflow...');
                    
                    let promises = [];
                    non_promo.forEach(function(row) {
                        let wh = values['wh_' + row.name];
                        promises.push(frappe.client.set_value(row.doctype, row.name, 'warehouse', wh));
                    });
                    
                    Promise.all(promises).then(() => {
                        return execute_bulk_action(doc.name, action);
                    }).then(() => {
                        frappe.dom.unfreeze();
                        resolve();
                    }).catch(err => {
                        frappe.dom.unfreeze();
                        reject(err);
                    });
                }
            });

            d.onhide = function() {
                if (!confirmed) reject('cancelled');
            };

            d.fields_dict.bulk_warehouse.$input.on('change', function() {
                const val = $(this).val();
                if (!val) return;
                non_promo.forEach(function(row) { d.set_value('wh_' + row.name, val); });
            });

            d.show();
        });
    });
}

function execute_bulk_action(docname, action) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'frappe.model.workflow.bulk_workflow_approval',
            args: {
                docnames: JSON.stringify([docname]),
                doctype: 'Order Form',
                action: action
            },
            callback: function(r) {
                if (r.message) resolve();
                else reject('Workflow action failed.');
            },
            error: function(err) {
                reject(err);
            }
        });
    });
}
"""

if "List View Workflow Interceptor" not in old_script:
    new_script = old_script + "\n" + new_logic
    roqson.update_doc("Client Script", "Order Form List - Master", {"script": new_script})
    print("List View script updated with warehouse assignment logic.")
else:
    print("Logic already injected.")
