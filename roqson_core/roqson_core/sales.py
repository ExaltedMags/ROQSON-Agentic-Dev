import frappe

# Sales DocType Event handlers — populated in Phase 5.6.
# 2 scripts to port (see ARCHITECTURE.md § sales.py).


def before_save(doc, method):
    # Ported from Server Script: "Auto Cancel Order on Sales Cancellation"
    old_doc = doc.get_doc_before_save()
    old_status = old_doc.status if old_doc else ""

    if doc.status == "Cancelled" and old_status != "Cancelled":
        allowed_roles = ["Sales", "Sales Manager", "Sales User", "System Manager", "Administrator"]
        user_roles = frappe.get_roles(frappe.session.user)
        has_permission = any(r in user_roles for r in allowed_roles)

        if not has_permission:
            frappe.throw("Only Sales role and Admin can cancel a Sales record directly.")

        if doc.order_ref:
            order_doc = frappe.get_doc("Order Form", doc.order_ref)
            if order_doc.workflow_state != "Canceled":
                order_doc.workflow_state = "Canceled"
                order_doc.save(ignore_permissions=True)


def after_save(doc, method):
    # Ported from Server Script: "Sales Inventory Stock Out"
    old_doc = doc.get_doc_before_save()
    old_status = old_doc.status if old_doc else ""
    new_status = doc.status

    if doc.order_ref:
        # Sync unreserve flags on inventory ledger rows
        unreserved_items = {item.item: item.get("is_unreserved") or 0 for item in doc.items if item.item}

        ledgers = frappe.get_all("Inventory Ledger", filters={"order_no": doc.order_ref})
        for l in ledgers:
            ledger = frappe.get_doc("Inventory Ledger", l.name)
            ledger_changed = False

            for r in ledger.table_jflv:
                is_unreserved = unreserved_items.get(r.product, 0)

                if ledger.movement_type == "Reserved":
                    expected_reserved = 0 if is_unreserved else r.qty
                    if r.qty_reserved != expected_reserved:
                        r.qty_reserved = expected_reserved
                        ledger_changed = True

                elif ledger.movement_type == "Out":
                    expected_out = 0 if is_unreserved else r.qty
                    if r.qty_out != expected_out:
                        r.qty_out = expected_out
                        ledger_changed = True

            if ledger_changed:
                ledger.save(ignore_permissions=True)

    # Handle status transitions
    if old_doc and new_status != old_status:
        movement_type = None
        if new_status == "Received":
            movement_type = "Out"
        elif new_status == "Failed":
            movement_type = "Return"

        if movement_type and doc.order_ref:
            unreserved_items = {item.item: item.get("is_unreserved") or 0 for item in doc.items if item.item}
            ledgers = frappe.get_all("Inventory Ledger", filters={"order_no": doc.order_ref})
            for l in ledgers:
                ledger = frappe.get_doc("Inventory Ledger", l.name)
                ledger.movement_type = movement_type

                for r in ledger.table_jflv:
                    is_unreserved = unreserved_items.get(r.product, 0)
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
                log = (log + "\n" if log else "") + timeline_entry
                ledger.db_set("stock_movement_log", log, update_modified=False)

                ledger.save(ignore_permissions=True)
