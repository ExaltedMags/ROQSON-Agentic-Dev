"""
Step 1 — Create Receipt DocTypes
Creates:
  1A. Receipt Apply To  (child table, istable: 1)
  1B. Receipt           (header, submittable, autoname: ARP-.YYYY.-.####)

Run AFTER Step 0 pre-flight.
"""

import roqson
import requests
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": "token " + key + ":" + secret}
BASE = "https://roqson-industrial-sales.s.frappe.cloud"


# ── Helpers ───────────────────────────────────────────────────────────────────

def doctype_exists(name):
    try:
        roqson.get_doc("DocType", name)
        return True
    except Exception:
        return False


def create_doctype(payload):
    r = requests.post(BASE + "/api/resource/DocType", json=payload, headers=headers)
    if r.status_code not in (200, 201):
        print("ERROR creating " + payload["name"] + ": " + str(r.status_code))
        print(r.text[:500])
        raise Exception("DocType creation failed: " + payload["name"])
    print("Created DocType: " + payload["name"])
    return r.json()


# ─────────────────────────────────────────────────────────────────────────────
# 1A  Receipt Apply To  (child table)
# ─────────────────────────────────────────────────────────────────────────────

CHILD_NAME = "Receipt Apply To"

if doctype_exists(CHILD_NAME):
    print(CHILD_NAME + " already exists — skipping.")
else:
    child_payload = {
        "doctype": "DocType",
        "name": CHILD_NAME,
        "module": "Custom",
        "istable": 1,
        "custom": 1,
        "fields": [
            {
                "fieldname": "sales_no",
                "label": "Sales No.",
                "fieldtype": "Link",
                "options": "Sales",
                "reqd": 1,
                "in_list_view": 1,
            },
            {
                "fieldname": "sale_date",
                "label": "Sale Date",
                "fieldtype": "Date",
                "read_only": 1,
                "fetch_from": "sales_no.creation_date",
            },
            {
                "fieldname": "due_date",
                "label": "Due Date",
                "fieldtype": "Date",
            },
            {
                "fieldname": "sale_grand_total",
                "label": "Sale Grand Total",
                "fieldtype": "Currency",
                "read_only": 1,
                "fetch_from": "sales_no.grand_total",
            },
            {
                "fieldname": "amount_applied",
                "label": "Amount Applied",
                "fieldtype": "Currency",
                "reqd": 1,
                "in_list_view": 1,
            },
            {
                "fieldname": "outstanding_balance",
                "label": "Outstanding Balance",
                "fieldtype": "Currency",
                "read_only": 1,
                "in_list_view": 1,
            },
        ],
        "permissions": [
            {"role": "Accounting",       "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "Administrator",    "read": 1, "write": 1, "create": 1, "delete": 1},
            {"role": "System Manager",   "read": 1, "write": 1, "create": 1, "delete": 1},
        ],
    }
    # Re-index fields
    for i, f in enumerate(child_payload["fields"]):
        f["idx"] = i + 1
        f["doctype"] = "DocField"
    create_doctype(child_payload)


# ─────────────────────────────────────────────────────────────────────────────
# 1B  Receipt  (header, submittable)
# ─────────────────────────────────────────────────────────────────────────────

HEADER_NAME = "Receipt"

if doctype_exists(HEADER_NAME):
    print(HEADER_NAME + " already exists — skipping.")
else:
    receipt_fields = [
        # ── Receipt Information ────────────────────────────────────────────
        {
            "fieldname": "sec_receipt_info",
            "label": "Receipt Information",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "date",
            "label": "Date",
            "fieldtype": "Date",
            "default": "Today",
            "reqd": 1,
        },
        {
            "fieldname": "customer",
            "label": "Customer",
            "fieldtype": "Link",
            "options": "Customer Information",
            "reqd": 1,
        },
        {
            "fieldname": "col_break_1",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "user",
            "label": "User",
            "fieldtype": "Data",
            "read_only": 1,
            "default": "__user",
        },
        {
            "fieldname": "ref_no",
            "label": "Ref No.",
            "fieldtype": "Data",
        },
        # ── Customer ──────────────────────────────────────────────────────
        {
            "fieldname": "sec_customer",
            "label": "Customer",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "salesman",
            "label": "Salesman",
            "fieldtype": "Link",
            "options": "Sales Personnel",
        },
        {
            "fieldname": "payment_group",
            "label": "Payment Group",
            "fieldtype": "Data",
        },
        {
            "fieldname": "col_break_2",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "pr_no",
            "label": "PR No.",
            "fieldtype": "Data",
        },
        {
            "fieldname": "advances",
            "label": "Advances",
            "fieldtype": "Check",
        },
        # ── Payment Details ────────────────────────────────────────────────
        {
            "fieldname": "sec_payment",
            "label": "Payment Details",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "payment_type",
            "label": "Payment Type",
            "fieldtype": "Select",
            "options": "\nCash\nCheck\nBank Transfer",
            "reqd": 1,
        },
        {
            "fieldname": "remarks",
            "label": "Remarks",
            "fieldtype": "Text",
        },
        {
            "fieldname": "col_break_3",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "net_amount",
            "label": "Net Amount",
            "fieldtype": "Currency",
            "reqd": 1,
        },
        {
            "fieldname": "outstanding_balance",
            "label": "Outstanding Balance",
            "fieldtype": "Currency",
            "read_only": 1,
        },
        # ── Check Details ──────────────────────────────────────────────────
        {
            "fieldname": "sec_check",
            "label": "Check Details",
            "fieldtype": "Section Break",
            "depends_on": "eval:doc.payment_type=='Check'",
        },
        {
            "fieldname": "bank",
            "label": "Bank",
            "fieldtype": "Data",
        },
        {
            "fieldname": "check_no",
            "label": "Check No.",
            "fieldtype": "Data",
        },
        {
            "fieldname": "check_date",
            "label": "Check Date",
            "fieldtype": "Date",
        },
        {
            "fieldname": "col_break_4",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "deposit_bank_account",
            "label": "Deposit Bank Account",
            "fieldtype": "Data",
        },
        {
            "fieldname": "deposit_date",
            "label": "Deposit Date",
            "fieldtype": "Date",
        },
        # ── Bank Transfer Details ──────────────────────────────────────────
        {
            "fieldname": "sec_bt",
            "label": "Bank Transfer Details",
            "fieldtype": "Section Break",
            "depends_on": "eval:doc.payment_type=='Bank Transfer'",
        },
        {
            "fieldname": "bt_bank_account",
            "label": "Bank Account",
            "fieldtype": "Data",
        },
        {
            "fieldname": "col_break_5",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "bt_ref_no",
            "label": "Transfer Ref No.",
            "fieldtype": "Data",
        },
        # ── Apply To ──────────────────────────────────────────────────────
        {
            "fieldname": "sec_apply_to",
            "label": "Apply To",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "apply_to",
            "label": "Apply To",
            "fieldtype": "Table",
            "options": "Receipt Apply To",
            "reqd": 1,
        },
        # ── Signatories ───────────────────────────────────────────────────
        {
            "fieldname": "sec_signatories",
            "label": "Signatories",
            "fieldtype": "Section Break",
        },
        {
            "fieldname": "prepared_by",
            "label": "Prepared By",
            "fieldtype": "Data",
        },
        {
            "fieldname": "col_break_6",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "checked_by",
            "label": "Checked By",
            "fieldtype": "Data",
        },
        {
            "fieldname": "col_break_7",
            "fieldtype": "Column Break",
        },
        {
            "fieldname": "approved_by",
            "label": "Approved By",
            "fieldtype": "Data",
        },
    ]

    # Re-index
    for i, f in enumerate(receipt_fields):
        f["idx"] = i + 1
        f["doctype"] = "DocField"

    receipt_payload = {
        "doctype": "DocType",
        "name": HEADER_NAME,
        "module": "Custom",
        "custom": 1,
        "is_submittable": 1,
        "autoname": "ARP-.YYYY.-.####",
        "fields": receipt_fields,
        "permissions": [
            {
                "role": "Accounting",
                "read": 1, "write": 1, "create": 1, "delete": 0,
                "submit": 1, "cancel": 1,
            },
            {
                "role": "Administrator",
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 1, "cancel": 1,
            },
            {
                "role": "System Manager",
                "read": 1, "write": 1, "create": 1, "delete": 1,
                "submit": 1, "cancel": 1,
            },
        ],
    }
    create_doctype(receipt_payload)


# ── Verify ────────────────────────────────────────────────────────────────────
print("\nVerifying...")
try:
    d = roqson.get_doc("DocType", CHILD_NAME)
    print("OK: " + CHILD_NAME + " found with " + str(len(d.get("fields", []))) + " fields")
except Exception as e:
    print("FAIL: " + CHILD_NAME + " — " + str(e))

try:
    d = roqson.get_doc("DocType", HEADER_NAME)
    print("OK: " + HEADER_NAME + " found, autoname=" + str(d.get("autoname")) + ", submittable=" + str(d.get("is_submittable")))
except Exception as e:
    print("FAIL: " + HEADER_NAME + " — " + str(e))
