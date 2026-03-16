"""
Step 2 — Create Receipt Server Scripts
Creates:
  A. Receipt: Update Sales on Submit   (DocType Event — On Submit)
  B. Receipt: Revert Sales on Cancel   (DocType Event — Before Cancel)
  C. get_receivable_sales_for_customer (API)

RestrictedPython compliant: no f-strings, no .format(), string concat only.
"""

import roqson
import requests
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": "token " + key + ":" + secret}
BASE = "https://roqson-industrial-sales.s.frappe.cloud"


def upsert_server_script(name, payload):
    """Create or update a Server Script by name."""
    try:
        roqson.get_doc("Server Script", name)
        # Exists — update
        roqson.update_doc("Server Script", name, payload)
        print("Updated: " + name)
    except Exception:
        # Doesn't exist — create
        payload["doctype"] = "Server Script"
        payload["name"] = name
        r = requests.post(BASE + "/api/resource/Server Script", json=payload, headers=headers)
        if r.status_code not in (200, 201):
            print("ERROR creating " + name + ": " + str(r.status_code))
            print(r.text[:500])
            raise Exception("Server Script creation failed: " + name)
        print("Created: " + name)


# ─────────────────────────────────────────────────────────────────────────────
# Script A — Receipt: Update Sales on Submit
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_A_NAME = "Receipt: Update Sales on Submit"

script_a_body = """# Receipt: Update Sales on Submit
# DocType Event: Receipt -- On Submit
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

    if outstanding == 0 and sale.status == "Received":
        frappe.db.set_value("Sales", row.sales_no, "status", "Completed", update_modified=True)
"""

upsert_server_script(SCRIPT_A_NAME, {
    "script_type": "DocType Event",
    "reference_doctype": "Receipt",
    "doctype_event": "After Submit",
    "script": script_a_body,
    "disabled": 0,
})


# ─────────────────────────────────────────────────────────────────────────────
# Script B — Receipt: Revert Sales on Cancel
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_B_NAME = "Receipt: Revert Sales on Cancel"

script_b_body = """# Receipt: Revert Sales on Cancel
# DocType Event: Receipt -- Before Cancel
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
    total_applied = sum(r.amount_applied or 0 for r in remaining if r.parent != doc.name)

    outstanding = sale.grand_total - total_applied
    if outstanding < 0:
        outstanding = 0

    frappe.db.set_value("Sales", row.sales_no, "outstanding_balance", outstanding, update_modified=False)

    if outstanding > 0 and sale.status == "Completed":
        frappe.db.set_value("Sales", row.sales_no, "status", "Received", update_modified=True)
"""

upsert_server_script(SCRIPT_B_NAME, {
    "script_type": "DocType Event",
    "reference_doctype": "Receipt",
    "doctype_event": "Before Cancel",
    "script": script_b_body,
    "disabled": 0,
})


# ─────────────────────────────────────────────────────────────────────────────
# Script C — get_receivable_sales_for_customer (API)
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_C_NAME = "get_receivable_sales_for_customer"

script_c_body = """# get_receivable_sales_for_customer
# API Script: returns Received Sales for a given customer.
# Used by Receipt Apply To grid to filter sales_no Link field.

customer = frappe.form_dict.get("customer", "")

filters = {"status": "Received"}
if customer:
    filters["customer_link"] = customer

sales = frappe.get_all(
    "Sales",
    filters=filters,
    fields=["name", "grand_total", "creation_date", "outstanding_balance"],
    order_by="creation_date desc",
    limit=200
)

frappe.response["message"] = sales
"""

upsert_server_script(SCRIPT_C_NAME, {
    "script_type": "API",
    "api_method": "get_receivable_sales_for_customer",
    "reference_doctype": "",
    "script": script_c_body,
    "disabled": 0,
    "allow_guest": 0,
})


# ── Verify ────────────────────────────────────────────────────────────────────
print("\nVerifying Receipt server scripts...")
result = roqson.get_scripts_for_doctype("Receipt")
print("Server scripts found: " + str(len(result.get("server", []))))
for s in result.get("server", []):
    print("  - " + s["name"] + " | " + str(s.get("script_type")))

# Also check API script
all_server = roqson.list_docs(
    "Server Script",
    fields=["name", "script_type", "api_method", "disabled"],
    filters=[["api_method", "=", "get_receivable_sales_for_customer"]],
    limit=5
)
print("API script check: " + str(len(all_server)) + " found")
for s in all_server:
    print("  - " + s["name"] + " | method: " + str(s.get("api_method")))
