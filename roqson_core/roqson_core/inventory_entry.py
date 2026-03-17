import frappe

# Inventory Entry DocType Event handlers — populated in Phase 5.4.
# 1 script to port (see ARCHITECTURE.md § inventory_entry.py).


def after_insert(doc, method):
    # Ported from Server Script: "Inventory Stock In"
    existing = frappe.get_all(
        "Inventory Ledger",
        filters={"stock_entry": doc.name},
        limit=1
    )

    if not existing:
        ledger_data = {
            "doctype": "Inventory Ledger",
            "movement_type": "In",
            "stock_entry": doc.name,
            "warehouse": doc.warehouse,
            "date_and_time": frappe.utils.now_datetime(),
            "remarks": "Stock In from Inventory Entry",
            "table_jflv": []
        }

        for row in doc.table_rvnc or []:
            ledger_data["table_jflv"].append({
                "product": row.product,
                "unit": row.unit_of_measurement,
                "qty": float(row.qty or 0),
                "unit_cost": float(row.unit_cost or 0)
            })

        frappe.get_doc(ledger_data).insert(ignore_permissions=True)
