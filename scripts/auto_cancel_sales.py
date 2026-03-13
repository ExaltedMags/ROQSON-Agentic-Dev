# Auto Cancel Sales on Order Cancellation
# DocType Event: Order Form — After Save (Submitted Document)

old_doc = doc.get_doc_before_save()
if not old_doc:
    old_wf = ""
else:
    old_wf = old_doc.workflow_state or ""

# Only trigger on transition TO Canceled
if doc.workflow_state == "Canceled" and old_wf != "Canceled":
    sales_ref = doc.get("sales_ref")
    if sales_ref and frappe.db.exists("Sales", sales_ref):
        sales_doc = frappe.get_doc("Sales", sales_ref)
        if sales_doc.status != "Cancelled":
            frappe.db.set_value("Sales", sales_ref, "status", "Cancelled",
                                update_modified=True)
