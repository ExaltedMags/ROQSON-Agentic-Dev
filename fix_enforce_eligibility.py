import roqson

script = """
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
    frappe.throw("Sales record " + str(first_sales_name) + " not found.")

# Updated eligibility check: must be Pending or Dispatching (if editing an existing trip)
if first_sales.get("status") not in ["Pending", "Dispatching"]:
    frappe.throw(
        "Sales record " + str(first_sales_name) + " is not eligible for dispatch (status must be Pending, got " + str(first_sales.get("status")) + ")."
    )

first_outlet = first_sales.get("customer_link")
if not first_outlet:
    frappe.throw("Sales record " + str(first_sales_name) + " has no customer. Cannot create Trip Ticket.")  

doc.set(TRIP_OUTLET_FIELD, first_outlet)
doc.set(TRIP_CONTACT_FIELD, first_sales.get("contact_number") or "")
doc.set(TRIP_ADDRESS_FIELD, first_sales.get("address") or "")

seen = {}
for r in rows:
    sales_name = r.get(CHILD_SALES_FIELD)
    if not sales_name:
        continue

    if sales_name in seen:
        frappe.throw("Duplicate Sales record in Trip Ticket: " + str(sales_name))
    seen[sales_name] = 1

    vals = frappe.db.get_value(
        "Sales", sales_name,
        ["status", "customer_link"],
        as_dict=True
    ) or {}

    outlet = vals.get("customer_link")
    status = vals.get("status")

    if not outlet:
        frappe.throw("Sales record " + str(sales_name) + " has no customer.")

    if outlet != first_outlet:
        frappe.throw(
            "Sales record " + str(sales_name) + " belongs to outlet '" + str(outlet) + "', but Trip Ticket is locked to '" + str(first_outlet) + "'."
        )

    # Allow Pending for new assignments, or Dispatching for current assignments
    if status not in ["Pending", "Dispatching"]:
        frappe.throw(
            "Sales record " + str(sales_name) + " is not eligible (status must be Pending, got " + str(status) + ")."
        )
"""

print("Fixing restricted syntax in Server Script: Enforce Eligibility")
roqson.update_doc("Server Script", "Enforce Eligibility", {"script": script})
