import frappe


def before_cancel(doc, method):
    # Ported from Server Script: "Receipt: Revert Sales on Cancel"
    # Recalculates outstanding_balance excluding this Receipt; reverts Completed to Received.
    for row in (doc.apply_to or []):
        if not row.sales_no:
            continue

        sale = frappe.get_doc("Sales", row.sales_no)

        # Sum submitted rows excluding this receipt's parent
        remaining = frappe.get_all(
            "Receipt Apply To",
            filters={"sales_no": row.sales_no, "docstatus": 1},
            fields=["amount_applied", "parent"]
        )
        total_applied = 0
        for r in remaining:
            if r.parent != doc.name:
                total_applied += r.amount_applied or 0

        outstanding = sale.grand_total - total_applied
        if outstanding < 0:
            outstanding = 0

        frappe.db.set_value("Sales", row.sales_no, "outstanding_balance", outstanding, update_modified=False)

        if outstanding > 0 and sale.status == "Completed":
            frappe.db.set_value("Sales", row.sales_no, "status", "Received", update_modified=True)


def on_submit(doc, method):
    # Ported from Server Script: "Receipt: Update Sales on Submit"
    # Updates outstanding_balance on Sales; marks Completed when balance = 0.
    for row in (doc.apply_to or []):
        if not row.sales_no:
            continue

        sale = frappe.get_doc("Sales", row.sales_no)

        # Sum all SUBMITTED Receipt Apply To rows for this Sales record
        all_applied = frappe.get_all(
            "Receipt Apply To",
            filters={"sales_no": row.sales_no, "docstatus": 1},
            fields=["amount_applied"]
        )
        total_applied = sum(r.amount_applied or 0 for r in all_applied)

        # Placeholder for BIR 2307 withholding tax (slot in here when ready)
        withheld_amount = 0

        outstanding = sale.grand_total - total_applied - withheld_amount
        if outstanding < 0:
            outstanding = 0

        frappe.db.set_value("Sales", row.sales_no, "outstanding_balance", outstanding, update_modified=False)
        frappe.db.set_value("Receipt Apply To", row.name, "outstanding_balance", outstanding, update_modified=False)

        # Use fresh DB read for status to avoid stale doc cache
        live_status = frappe.db.get_value("Sales", row.sales_no, "status")
        if outstanding == 0 and live_status == "Received":
            frappe.db.set_value("Sales", row.sales_no, "status", "Completed", update_modified=True)
