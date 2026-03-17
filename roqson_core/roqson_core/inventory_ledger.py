import frappe

# Inventory Ledger DocType Event handlers — populated in Phase 5.5.
# 3 scripts to port (see ARCHITECTURE.md § inventory_ledger.py).
# Note: "Inventory Entry Quantity" has no reference_doctype set in the live
# instance but its body confirms it targets Inventory Ledger docs.
# Set reference_doctype = "Inventory Ledger" on the live script before Phase 5.


def before_insert(doc, method):
    # Ported from Server Script: "Source"
    if doc.order_no or doc.stock_entry:
        doc.source_type = "System"
    else:
        doc.source_type = "Manual Adjustment"

    if not doc.created_by:
        doc.created_by = frappe.session.user


def after_insert(doc, method):
    # Ported from Server Script: "Inventory Notifications"
    affected_products = {
        row.product
        for row in (doc.get_all_children())
        if row.product
    }

    if not affected_products:
        return

    target_roles = [
        "President", "Stock Manager", "Sales", "Manager",
        "Purchaser", "Dispatcher", "Administrator"
    ]

    recipient_users = frappe.db.sql("""
        SELECT DISTINCT hr.parent
        FROM `tabHas Role` hr
        INNER JOIN `tabUser` u ON u.name = hr.parent
        WHERE hr.role IN %(roles)s
        AND u.enabled = 1
    """, {"roles": tuple(target_roles)}, pluck="parent")

    data = frappe.db.sql("""
        SELECT
            t.product,
            p.item_description,
            p.reorder_level,
            SUM(CASE WHEN l.movement_type = 'In' THEN t.qty ELSE 0 END)
            - SUM(CASE WHEN l.movement_type = 'Out' THEN t.qty ELSE 0 END)
            - SUM(CASE WHEN l.movement_type = 'Reserved' THEN t.qty ELSE 0 END)
            AS available_qty
        FROM `tabInventory Ledger` l
        JOIN `tabInventory Ledger Table` t ON t.parent = l.name
        LEFT JOIN `tabProduct` p ON p.name = t.product
        WHERE t.product IN %(products)s
        GROUP BY t.product, p.item_description, p.reorder_level
    """, {"products": tuple(affected_products)}, as_dict=True)

    colors = {
        "STOCKOUT": "#000000",
        "CRITICAL": "#d32f2f",
        "WARNING": "#f9a825",
        "MONITOR": "#1565c0"
    }

    notifications_to_insert = []
    status_updates = []

    for row in data:
        if not row.reorder_level or float(row.reorder_level) == 0:
            continue

        reorder = float(row.reorder_level)
        available = float(row.available_qty or 0)

        if available <= 0:
            current_status = "STOCKOUT"
        elif available <= reorder * 0.2:
            current_status = "CRITICAL"
        elif available <= reorder:
            current_status = "WARNING"
        elif available <= reorder * 1.5:
            current_status = "MONITOR"
        else:
            current_status = "OK"

        previous_status = frappe.db.get_value("Product", row.product, "last_stock_status") or None

        if previous_status == current_status:
            continue

        status_updates.append((row.product, current_status))

        if current_status == "OK":
            continue

        product_name = row.item_description or row.product
        color = colors.get(current_status)
        styled_status = f'<span style="color:{color};font-weight:800;"> {current_status}</span>'
        subject = f"{styled_status}:<br><b>{product_name}</b><br>{int(available)} units available"

        for user in recipient_users:
            notifications_to_insert.append({
                "for_user": user,
                "type": "Alert",
                "subject": subject,
                "email_content": subject,
                "link": "/app/query-report/Inventory%20Balance%20Report",
                "document_type": "Product",
                "document_name": row.product
            })

    for notif in notifications_to_insert:
        try:
            n = frappe.new_doc("Notification Log")
            n.update(notif)
            n.insert(ignore_permissions=True)
        except Exception:
            frappe.log_error(frappe.get_traceback(), "Stock Notification Error")

    for product, status in status_updates:
        frappe.db.set_value("Product", product, "last_stock_status", status, update_modified=False)


def on_update_after_submit(doc, method):
    # Ported from Server Script: "Inventory Entry Quantity"
    bal_list = frappe.get_all("Inventory Balance",
        filters={"item": doc.product, "warehouse": doc.warehouse},
        limit=1
    )

    if bal_list:
        bal = frappe.get_doc("Inventory Balance", bal_list[0].name)
    else:
        bal = frappe.get_doc({
            "doctype": "Inventory Balance",
            "item": doc.product,
            "warehouse": doc.warehouse,
            "on_hand_qty": 0.0,
            "committed_qty": 0.0
        })

    bal.on_hand_qty = bal.on_hand_qty + doc.quantity
    bal.available_qty = bal.on_hand_qty - bal.committed_qty
    bal.last_updated = frappe.utils.now()
    bal.save()
