import roqson

doc = roqson.get_doc("Client Script", "Order Form List - Master")
old_script = doc.get("script", "")

# We will replace the open_listview_warehouse_dialog and execute_bulk_action functions
# to fix the save concurrency and unfreezing issue.

new_funcs = """
function open_listview_warehouse_dialog(doc, action, listview, resolve, reject) {
    const rows = doc.table_mkaq || [];
    const non_promo = rows.filter(r => !r.is_promo_reward && r.items);

    if (!non_promo.length) {
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
                    
                    // Update document directly instead of individual child rows
                    non_promo.forEach(function(row) {
                        row.warehouse = values['wh_' + row.name];
                    });
                    
                    frappe.call({
                        method: 'frappe.client.save',
                        args: { doc: doc },
                        callback: function(r) {
                            if (!r.exc) {
                                execute_bulk_action(doc.name, action)
                                    .then(() => {
                                        frappe.dom.unfreeze();
                                        resolve();
                                    })
                                    .catch(err => {
                                        frappe.dom.unfreeze();
                                        reject(err);
                                    });
                            } else {
                                frappe.dom.unfreeze();
                                reject('Save failed');
                            }
                        },
                        error: function(err) {
                            frappe.dom.unfreeze();
                            reject(err);
                        }
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
                if (r.message && r.message.failed_transactions && Object.keys(r.message.failed_transactions).length > 0) {
                    reject('Workflow validation failed for ' + docname);
                } else if (!r.exc) {
                    resolve();
                } else {
                    reject('Workflow action failed.');
                }
            },
            error: function(err) {
                reject(err);
            }
        });
    });
}
"""

# Extract the beginning and replace
start_idx = old_script.find("function open_listview_warehouse_dialog")
if start_idx != -1:
    script_top = old_script[:start_idx]
    final_script = script_top + new_funcs
    roqson.update_doc("Client Script", "Order Form List - Master", {"script": final_script})
    print("List View script patched!")
else:
    print("Could not find the function to replace.")
