import frappe

# Price Change Request DocType Event handlers — populated in Phase 5.3.


def after_save(doc, method):
    # Ported from Server Script: "Process PCR Approval"
    if doc.status == "Approved" and doc.order_form:
        pending = frappe.db.count("Price Change Request", {
            "order_form": doc.order_form,
            "status": "Pending"
        })

        if pending == 0:
            order_state = frappe.db.get_value("Order Form", doc.order_form, "workflow_state")
            if order_state == "Needs Review":
                user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user

                frappe.db.set_value("Order Form", doc.order_form, {
                    "workflow_state": "Approved",
                    "docstatus": 1,
                    "approved_by": user_name
                }, update_modified=False)

                existing = frappe.get_all("Sales", filters={"order_ref": doc.order_form}, limit=1)
                if existing:
                    if not frappe.db.get_value("Order Form", doc.order_form, "sales_ref"):
                        frappe.db.set_value("Order Form", doc.order_form, "sales_ref",
                                            existing[0].name, update_modified=False)
                else:
                    order_doc = frappe.get_doc("Order Form", doc.order_form)
                    items = []
                    for row in (order_doc.get("table_mkaq") or []):
                        if row.get("items"):
                            items.append({
                                "doctype": "Sales Items Table",
                                "item": row.get("items"),
                                "qty": row.get("qty") or 0,
                                "unit": row.get("unit") or "",
                                "unit_price": row.get("price") or 0,
                                "total": row.get("total_price") or 0,
                                "warehouse": row.get("warehouse") or "",
                                "is_promo": row.get("is_promo_reward") or 0,
                            })

                    sales = frappe.get_doc({
                        "doctype": "Sales",
                        "status": "Pending",
                        "fulfillment_type": order_doc.get("fulfillment_type") or "Delivery",
                        "order_ref": order_doc.name,
                        "customer_link": order_doc.get("outlet") or "",
                        "customer_name": order_doc.get("name_of_outlet") or order_doc.get("outlet") or "",
                        "address": order_doc.get("address") or "",
                        "contact_number": order_doc.get("contact_number") or "",
                        "grand_total": order_doc.get("grand_total") or 0,
                        "creation_date": frappe.utils.nowdate(),
                        "items": items,
                    })
                    sales.insert(ignore_permissions=True)
                    frappe.db.set_value("Order Form", order_doc.name, "sales_ref", sales.name,
                                        update_modified=False)
