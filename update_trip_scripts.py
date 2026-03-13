import roqson
import sys

# 1. Update Enforce Eligibility (Before Save)
enforce_eligibility_script = """
# Trip Ticket - Enforce Non-Bypassable Eligibility (Sales-based)
# DocType Event: Trip Ticket — Before Save

CHILD_TABLE_FIELD = "table_cpme"
CHILD_SALES_FIELD = "sales_no"

TRIP_OUTLET_FIELD = "outlet"
TRIP_CONTACT_FIELD = "contact_number"
TRIP_ADDRESS_FIELD = "address"
TRIP_CONTACT_PERSON_FIELD = "contact_person"

rows = doc.get(CHILD_TABLE_FIELD) or []

if not rows or not rows[0].get(CHILD_SALES_FIELD):
    frappe.throw("Row 1 must have a Sales No. before saving.")

first_sales_name = rows[0].get(CHILD_SALES_FIELD)
first_sales = frappe.db.get_value(
    "Sales",
    first_sales_name,
    ["status", "customer_link", "address", "contact_number"],
    as_dict=True
) or {}

if not first_sales:
    frappe.throw("Sales record {} not found.".format(first_sales_name))

# Updated eligibility check: must be Pending or Dispatching (if editing an existing trip)
if first_sales.get("status") not in ["Pending", "Dispatching"]:
    frappe.throw(
        "Sales record {} is not eligible for dispatch (status must be Pending, got {}).".format(first_sales_name, first_sales.get("status"))
    )

first_outlet = first_sales.get("customer_link")
if not first_outlet:
    frappe.throw("Sales record {} has no customer. Cannot create Trip Ticket.".format(first_sales_name))

doc.set(TRIP_OUTLET_FIELD, first_outlet)
doc.set(TRIP_CONTACT_FIELD, first_sales.get("contact_number") or "")
doc.set(TRIP_ADDRESS_FIELD, first_sales.get("address") or "")

seen = {}
for r in rows:
    sales_name = r.get(CHILD_SALES_FIELD)
    if not sales_name:
        continue

    if sales_name in seen:
        frappe.throw("Duplicate Sales record in Trip Ticket: {}".format(sales_name))
    seen[sales_name] = 1

    vals = frappe.db.get_value(
        "Sales", sales_name,
        ["status", "customer_link"],
        as_dict=True
    ) or {}

    outlet = vals.get("customer_link")
    status = vals.get("status")

    if not outlet:
        frappe.throw("Sales record {} has no customer.".format(sales_name))

    if outlet != first_outlet:
        frappe.throw(
            "Sales record {} belongs to outlet '{}', but Trip Ticket is locked to '{}'.".format(
                sales_name, outlet, first_outlet
            )
        )

    # Allow Pending for new assignments, or Dispatching for current assignments
    if status not in ["Pending", "Dispatching"]:
        frappe.throw(
            "Sales record {} is not eligible (status must be Pending, got {}).".format(
                sales_name, status
            )
        )
"""
print("Updating Server Script: Enforce Eligibility")
roqson.update_doc("Server Script", "Enforce Eligibility", {"script": enforce_eligibility_script})

# 2. Update Eligible Orders by Outlet (API)
eligible_orders_script = """
# Eligible Sales records for Trip Ticket creation
# Returns Sales records with status=Pending that aren't already on an active Trip Ticket
outlet = frappe.form_dict.get("outlet") or ""
current_trip = frappe.form_dict.get("current_trip") or ""

if not outlet:
    frappe.response["message"] = []
else:
    # Get Sales IDs already on active trip tickets (excluding current_trip)
    if current_trip:
        active_sales = frappe.db.sql(\"\"\"
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrip Ticket Table` ttt
            INNER JOIN `tabTrip Ticket` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
              AND tt.name != %(current_trip)s
        \"\"\", {"current_trip": current_trip}, as_dict=True)
    else:
        active_sales = frappe.db.sql(\"\"\"
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrip Ticket Table` ttt
            INNER JOIN `tabTrip Ticket` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
        \"\"\", as_dict=True)

    already_assigned = [r.sales_no for r in active_sales if r.sales_no]

    filters = {
        "status": "Pending",  # Updated to Pending
        "customer_link": outlet
    }
    eligible = frappe.get_all(
        "Sales",
        filters=filters,
        fields=["name", "customer_name", "grand_total", "order_ref", "sai_no"],
        limit_page_length=100
    )

    result = [s for s in eligible if s.name not in already_assigned]
    frappe.response["message"] = result
"""
print("Updating Server Script: Eligible Orders by Outlet")
roqson.update_doc("Server Script", "Eligible Orders by Outlet", {"script": eligible_orders_script})

# 3. Update Traceability (After Save)
traceability_script = """
# Trip Ticket -> Order Form & Sales Traceability
# DocType Event: Trip Ticket - After Save

if doc.table_cpme:
    for row in doc.table_cpme:
        # Link Order Form to Trip Ticket
        if row.order_no:
            frappe.db.set_value("Order Form", row.order_no, "trip_ticket", doc.name)
        
        # Mark linked Sales record as Dispatching
        if row.sales_no:
            current_status = frappe.db.get_value("Sales", row.sales_no, "status")
            if current_status == "Pending":
                frappe.db.set_value("Sales", row.sales_no, "status", "Dispatching")
"""
print("Updating Server Script: Trip Ticket and Order Form Traceability")
roqson.update_doc("Server Script", "Trip Ticket and Order Form Traceability", {"script": traceability_script})

# 4. Update Delivery Status Notification (Before Save)
# We use this to detect delivery_status change and update Sales record.
delivery_notif_script = """
# DocType Event Server Script (Before Save)
# Handles updating Sales status based on Trip Ticket delivery outcome

table_field = "table_cpme"
status_field = "delivery_status"
driver_field = "driverhelper"

old = doc.get_doc_before_save()

if old:
    old_status = (old.get(status_field) or "").strip()
    new_status = (doc.get(status_field) or "").strip()

    if new_status != old_status:
        # Map Successful -> Received, Failed -> Failed
        sales_target_status = None
        if new_status == "Successful":
            sales_target_status = "Received"
        elif new_status == "Failed":
            sales_target_status = "Failed"
            
        if sales_target_status and doc.get(table_field):
            for row in doc.get(table_field):
                if row.sales_no:
                    frappe.db.set_value("Sales", row.sales_no, "status", sales_target_status)
"""
print("Updating Server Script: Delivery Status Notification")
roqson.update_doc("Server Script", "Delivery Status Notification", {"script": delivery_notif_script})

print("Done updating Trip Ticket server scripts")
