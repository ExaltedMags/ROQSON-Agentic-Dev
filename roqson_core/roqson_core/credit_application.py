import frappe

# Credit Application DocType Event handlers — populated in Phase 5.8.
# 6 scripts to port (see ARCHITECTURE.md § credit_application.py).


def before_save(doc, method):
    # Ported from Server Script: "CA: Enforce Signatures"
    internal_roles = ["Sales", "Administrator", "Manager", "President"]
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, pluck="role")
    is_internal = any(role in user_roles for role in internal_roles)

    if doc.workflow_state == "Draft":
        if not is_internal:
            if not doc.owner_with_signature_and_printed_date:
                frappe.throw(
                    "Owner Signature is required before submitting the Credit Application."
                )

    if doc.workflow_state == "Approved":
        if not doc.ci_by:
            frappe.throw("CI Signature is required before approval.")
        if not doc.approved_by:
            frappe.throw("Acknowledged By signature is required before approval.")


def before_submit(doc, method):
    # Merged from Server Scripts: "CA: Supporting Documents" + "CA: Minimum"

    # CA: Supporting Documents
    sales_roles = ["Sales"]
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, pluck="role")
    is_sales = any(role in user_roles for role in sales_roles)

    if is_sales:
        required_categories = [
            "SEC Registration w/ Articles of Incorporation",
            "Latest Mayor's Permit",
            "Barangay Permit / Clearance",
            "Valid ID 1 (Government-issued)",
            "Valid ID 2 (Government-issued)",
            "DTI Registration"
        ]
        uploaded_categories = [
            row.document_category.strip()
            for row in (doc.get("table_ahmg") or [])
            if row.document_category and row.attachment
        ]
        missing = [c for c in required_categories if c.strip() not in uploaded_categories]
        if missing:
            frappe.throw(
                "The following required documents must be uploaded before submission:<br><br>"
                + "<br>".join(missing)
            )

    # CA: Minimum
    override_roles = ["President", "Manager"]
    has_override = any(role in user_roles for role in override_roles)

    if not has_override:
        supplier_references = doc.get("supplier_reference_table") or []
        if len(supplier_references) < 3:
            frappe.throw(
                "A minimum of three (3) Supplier References is required. "
                "If fewer are provided, only a Manager may submit this Credit Application."
            )


def after_save(doc, method):
    # Ported from Server Script: "CA: Update Credit Approval"

    if doc.unlimited_credit and doc.app_credit_line:
        frappe.throw(
            "Please choose only one: either enter a Requested Credit Line or select Unlimited Credit."
        )

    if not doc.unlimited_credit and not doc.app_credit_line:
        frappe.throw(
            "Please either enter a Requested Credit Line or select Unlimited Credit before submitting."
        )

    if doc.app_credit_line is not None and doc.app_credit_line < 0:
        frappe.throw("Requested Credit Line cannot be negative.")

    if doc.customer_information:
        customer = frappe.db.get_value(
            "Customer Information",
            doc.customer_information,
            ["credit_limit", "terms", "is_unlimited_credit"],
            as_dict=True
        )
        if not customer:
            frappe.throw("Customer Information record not found.")

        if doc.workflow_state == "Approved":
            doc.previous_credit_limit = customer.credit_limit
            doc.previous_terms = customer.terms

            if doc.unlimited_credit:
                new_limit, display_value, unlimited_flag = 0, "Unlimited", 1
            else:
                new_limit = doc.app_credit_line
                display_value = frappe.utils.fmt_money(doc.app_credit_line)
                unlimited_flag = 0

            frappe.db.set_value("Customer Information", doc.customer_information, {
                "terms": doc.app_credit_terms,
                "credit_limit": new_limit,
                "credit_limit_display": display_value,
                "is_unlimited_credit": unlimited_flag
            })

        if doc.workflow_state == "Canceled":
            previous_limit = doc.previous_credit_limit or 0
            previous_terms = doc.previous_terms

            if previous_limit == 0:
                display_value, previous_unlimited = "Unlimited", 1
            else:
                display_value = frappe.utils.fmt_money(previous_limit)
                previous_unlimited = 0

            frappe.db.set_value("Customer Information", doc.customer_information, {
                "terms": previous_terms,
                "credit_limit": previous_limit,
                "credit_limit_display": display_value,
                "is_unlimited_credit": previous_unlimited
            })


def on_update_after_submit(doc, method):
    # Merged from Server Scripts: "CA: Needs Review Notificaton" + "CA: For Completion Notif"
    old_doc = doc.get_doc_before_save()
    old_state = (old_doc.workflow_state or "") if old_doc else ""

    if doc.workflow_state == "Needs Review" and old_state != "Needs Review":
        users = frappe.db.sql("""
            SELECT parent FROM `tabHas Role`
            WHERE role = 'Credit Investigator' AND parenttype = 'User'
        """, as_dict=True)
        for u in users:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"{doc.customer_information} — {doc.name} ready for Credit Investigation",
                "for_user": u.parent,
                "type": "Alert",
                "document_type": "Credit Application",
                "document_name": doc.name
            }).insert(ignore_permissions=True)

    if doc.workflow_state == "For Completion" and old_state != "For Completion":
        users = frappe.db.sql("""
            SELECT parent FROM `tabHas Role`
            WHERE role = 'Sales' AND parenttype = 'User'
        """, as_dict=True)
        for u in users:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"{doc.customer_information} — {doc.name} requires Sales completion",
                "for_user": u.parent,
                "type": "Alert",
                "document_type": "Credit Application",
                "document_name": doc.name
            }).insert(ignore_permissions=True)
