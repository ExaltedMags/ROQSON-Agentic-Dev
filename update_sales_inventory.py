import roqson

script_name = "Sales Inventory Stock Out"
old_script = roqson.get_script_body("Server Script", script_name)

new_script = """# Handle Inventory Stock Out for Sales status transitions (Received/Failed)
# DocType Event: Sales - After Save

old_doc = doc.get_doc_before_save()
old_status = old_doc.status if old_doc else ""
new_status = doc.status

if doc.order_ref:
    # First, always handle unreserve logic for any state
    # This syncs the inventory ledger's reserved/out qty with the 'is_unreserved' flag in Sales Items Table
    
    unreserved_items = {}
    for item in doc.items:
        if item.item:
            unreserved_items[item.item] = getattr(item, 'is_unreserved', 0)

    ledgers = frappe.get_all("Inventory Ledger", filters={"order_no": doc.order_ref})
    for l in ledgers:
        ledger = frappe.get_doc("Inventory Ledger", l.name)
        ledger_changed = False
        
        for r in ledger.table_jflv:
            is_unreserved = unreserved_items.get(r.product, 0)
            
            # If ledger is in Reserved state
            if ledger.movement_type == "Reserved":
                expected_reserved = 0 if is_unreserved else r.qty
                if r.qty_reserved != expected_reserved:
                    r.qty_reserved = expected_reserved
                    ledger_changed = True
                    
            # If ledger is in Out state
            elif ledger.movement_type == "Out":
                expected_out = 0 if is_unreserved else r.qty
                if r.qty_out != expected_out:
                    r.qty_out = expected_out
                    ledger_changed = True

        if ledger_changed:
            ledger.save(ignore_permissions=True)

# Then, handle status transitions
if old_doc and new_status != old_status:
    movement_type = None
    if new_status == "Received":
        movement_type = "Out"
    elif new_status == "Failed":
        movement_type = "Return"

    if movement_type and doc.order_ref:
        ledgers = frappe.get_all("Inventory Ledger", filters={"order_no": doc.order_ref})
        for l in ledgers:
            ledger = frappe.get_doc("Inventory Ledger", l.name)
            ledger.movement_type = movement_type

            for r in ledger.table_jflv:
                # Get unreserved status again to be safe
                is_unreserved = 0
                for item in doc.items:
                    if item.item == r.product:
                        is_unreserved = getattr(item, 'is_unreserved', 0)
                        break

                if movement_type == "Out":
                    r.qty_out = 0 if is_unreserved else r.qty
                    r.qty_reserved = 0
                elif movement_type == "Return":
                    r.qty_reserved = 0
                    r.qty_out = 0

            user = frappe.session.user or doc.owner
            timestamp = frappe.utils.format_datetime(frappe.utils.now_datetime(), "yyyy-MM-dd HH:mm")
            timeline_entry = new_status + "|" + (user or "") + "|" + (timestamp or "")

            log = ledger.stock_movement_log or ""
            log = (log + "\\n" if log else "") + timeline_entry
            ledger.db_set("stock_movement_log", log, update_modified=False)

            ledger.save(ignore_permissions=True)
"""

roqson.safe_update_script("Server Script", script_name, new_script, auto_confirm=True)
