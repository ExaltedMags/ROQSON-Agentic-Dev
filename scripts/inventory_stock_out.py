if doc.docstatus == 2:
    pass
else:
    state_to_movement = {
        "Approved": "Reserved",   # Auto-reserve stock on Approval
        "Reserved": "Reserved",   # Manual Reserve Stock (idempotent, kept for compat)
        "Dispatched": "Out",
        "Delivered": "Out",
        "Delivery Failed": "Return",
        "Redeliver": "Reserved",
        "Canceled": "Released",
        "Rejected": "Released",
        "Paid": "Out",
        "Unpaid": "Out"
    }

    movement_type = state_to_movement.get(doc.workflow_state)

    if movement_type:
        old_doc = doc.get_doc_before_save()
        state_changed = old_doc and old_doc.workflow_state != doc.workflow_state

        # -- Stock availability check on Approval --
        if doc.workflow_state == "Approved" and state_changed:
            for row in (doc.table_mkaq or []):
                if not row.items or not row.warehouse:
                    continue
                avail_data = frappe.db.sql("""
                    SELECT
                        COALESCE(SUM(CASE WHEN l.movement_type='In'       THEN t.qty ELSE 0 END), 0)
                        - COALESCE(SUM(CASE WHEN l.movement_type='Out'      THEN t.qty ELSE 0 END), 0)
                        - COALESCE(SUM(CASE WHEN l.movement_type='Reserved' THEN t.qty ELSE 0 END), 0)
                        + COALESCE(SUM(CASE WHEN l.movement_type='Released' THEN t.qty ELSE 0 END), 0)
                        + COALESCE(SUM(CASE WHEN l.movement_type='Return'   THEN t.qty ELSE 0 END), 0)
                        AS available
                    FROM `tabInventory Ledger` l
                    JOIN `tabInventory Ledger Table` t ON t.parent = l.name
                    WHERE t.product = %s AND l.warehouse = %s
                """, (row.items, row.warehouse))
                available = float(avail_data[0][0] if avail_data and avail_data[0][0] is not None else 0)
                if float(row.qty or 0) > available:
                    frappe.throw(
                        "Insufficient stock for {} in {}. "
                        "Available: {:.0f}, Required: {}. "
                        "Please adjust the order or restock before approving.".format(
                            row.items, row.warehouse, available, int(row.qty or 0)
                        )
                    )

        user = frappe.session.user or doc.owner
        timestamp = frappe.utils.format_datetime(frappe.utils.now_datetime(), "yyyy-MM-dd HH:mm")
        timeline_entry = "{}|{}|{}".format(doc.workflow_state, user, timestamp)

        wh_groups = {}
        for row in (doc.table_mkaq or []):
            wh = row.get("warehouse")
            if not row.items or not wh:
                continue
            if wh not in wh_groups:
                wh_groups[wh] = []
            wh_groups[wh].append(row)

        for wh, rows in wh_groups.items():
            existing = frappe.get_all(
                "Inventory Ledger",
                filters={"order_no": doc.name, "warehouse": wh},
                order_by="creation asc",
                limit=1
            )

            if existing:
                ledger = frappe.get_doc("Inventory Ledger", existing[0].name)
                ledger.movement_type = movement_type

                for r in ledger.table_jflv:
                    if movement_type == "Reserved":
                        r.qty_reserved = r.qty
                        r.qty_out = 0
                    elif movement_type == "Released":
                        r.qty_reserved = 0
                        r.qty_out = 0
                    elif movement_type == "Out":
                        r.qty_out = r.qty
                        r.qty_reserved = 0
                    elif movement_type == "Return":
                        r.qty_reserved = 0
                        r.qty_out = 0

                if state_changed:
                    log = ledger.stock_movement_log or ""
                    log = (log + "\n" if log else "") + timeline_entry
                    ledger.db_set("stock_movement_log", log, update_modified=False)

                ledger.save(ignore_permissions=True)

            else:
                ledger = frappe.get_doc({
                    "doctype": "Inventory Ledger",
                    "movement_type": movement_type,
                    "order_no": doc.name,
                    "warehouse": wh,
                    "date_and_time": frappe.utils.now_datetime(),
                    "table_jflv": [],
                    "stock_movement_log": timeline_entry
                })

                for r in rows:
                    ledger.append("table_jflv", {
                        "product": r.items,
                        "unit": r.unit,
                        "qty": r.qty
                    })

                ledger.insert(ignore_permissions=True)
