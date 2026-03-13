import roqson

script_name = "Trip Ticket: Multi-Driver Operations"
old_script = roqson.get_script_body("Client Script", script_name)

old_sync_logic = """async function tt_sync_delivery_items(frm) {
  const salesRows = frm.doc[TT_SALES_TABLE] || [];
  const existing = {};
  (frm.doc[TT_ITEM_TABLE] || []).forEach(row => {
    existing[tt_delivery_key(row)] = {
      name: row.name,
      assigned_driver: row.assigned_driver || '',
      delivered: row.delivered || 0,
      sales_no: row.sales_no || '',
      order_no: row.order_no || '',
      sales_item_row: row.sales_item_row || '',
      item_code: row.item_code || '',
      item_name: row.item_name || '',
      quantity: row.quantity || 0,
      liters_per_unit: row.liters_per_unit || 0,
      total_liters: row.total_liters || 0
    };
  });

  frm.clear_table(TT_ITEM_TABLE);

  for (const salesRow of salesRows) {
    const salesNo = salesRow.sales_no;
    if (!salesNo) continue;
    const salesDoc = await tt_get_sales_doc(frm, salesNo);
    const items = (salesDoc && salesDoc.items) || [];
    for (const item of items) {
      const itemCode = item.item || '';
      const salesItemRow = item.name || '';
      const key = [salesNo, salesItemRow, itemCode].join('::');
      const previous = existing[key] || {};
      const child = frm.add_child(TT_ITEM_TABLE, {
        sales_no: salesNo,
        order_no: salesDoc.order_ref || '',
        sales_item_row: salesItemRow,
        item_code: itemCode,
        item_name: previous.item_name || itemCode,
        quantity: item.qty || 0,
        liters_per_unit: previous.liters_per_unit || 0,
        total_liters: previous.total_liters || 0,
        assigned_driver: previous.assigned_driver || '',
        delivered: previous.delivered || 0
      });
      if (previous.name) {
        child.name = previous.name;
      }
    }
  }
  frm.refresh_field(TT_ITEM_TABLE);
}"""

new_sync_logic = """async function tt_sync_delivery_items(frm) {
  const salesRows = frm.doc[TT_SALES_TABLE] || [];
  const existing = {};
  
  (frm.doc[TT_ITEM_TABLE] || []).forEach(row => {
    existing[tt_delivery_key(row)] = {
      name: row.name,
      assigned_driver: row.assigned_driver || '',
      delivered: row.delivered || 0,
      sales_no: row.sales_no || '',
      order_no: row.order_no || '',
      sales_item_row: row.sales_item_row || '',
      item_code: row.item_code || '',
      item_name: row.item_name || '',
      quantity: row.quantity || 0,
      liters_per_unit: row.liters_per_unit || 0,
      total_liters: row.total_liters || 0
    };
  });

  frm.clear_table(TT_ITEM_TABLE);

  for (const salesRow of salesRows) {
    const salesNo = salesRow.sales_no;
    if (!salesNo) continue;
    const salesDoc = await tt_get_sales_doc(frm, salesNo);
    const items = (salesDoc && salesDoc.items) || [];
    for (const item of items) {
      const itemCode = item.item || '';
      const salesItemRow = item.name || '';
      const key = [salesNo, salesItemRow, itemCode].join('::');
      const previous = existing[key] || {};
      
      let itemName = previous.item_name || itemCode;
      // Fetch actual item description if it's missing or still the code
      if (itemName === itemCode && itemCode) {
        try {
          let res = await frappe.db.get_value('Product', itemCode, 'item_description');
          if (res && res.message && res.message.item_description) {
            itemName = res.message.item_description;
          }
        } catch(e) {}
      }

      const child = frm.add_child(TT_ITEM_TABLE, {
        sales_no: salesNo,
        order_no: salesDoc.order_ref || '',
        sales_item_row: salesItemRow,
        item_code: itemCode,
        item_name: itemName,
        quantity: item.qty || 0,
        liters_per_unit: previous.liters_per_unit || 0,
        total_liters: previous.total_liters || 0,
        assigned_driver: previous.assigned_driver || '',
        delivered: previous.delivered || 0
      });
      
      // Removed the buggy child.name overwriting that causes the table UI to break and show labels
    }
  }
  frm.refresh_field(TT_ITEM_TABLE);
}"""

if old_sync_logic in old_script:
    new_script = old_script.replace(old_sync_logic, new_sync_logic)
    roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
    print("Script updated successfully.")
else:
    print("Could not find old sync logic in script.")
