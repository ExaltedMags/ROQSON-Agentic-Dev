"""
create_test_receipt_bundles.py
Creates 3 end-to-end test bundles: Order Form -> Sales -> Receipt

Bundle A -- CTMR-05130 (Orange TEST)   : Full cash payment  -> Sale = Completed
Bundle B -- CTMR-05136 (Apple TEST)    : Two partial checks -> Sale = Completed
Bundle C -- CTMR-05137 (Yahargul TEST) : Partial only       -> Sale stays Received

Pick-up fulfillment (skips Trip Ticket for speed).
"""

import sys
sys.path.insert(0, ".")
import roqson
import requests
import os
import time

key    = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": "token " + key + ":" + secret}
BASE    = "https://roqson-industrial-sales.s.frappe.cloud"


# ── Core helpers ──────────────────────────────────────────────────────────────

def apply_workflow(doctype, docname, action):
    r = requests.post(
        BASE + "/api/method/frappe.model.workflow.apply_workflow",
        json={"doc": roqson.get_doc(doctype, docname), "action": action},
        headers=headers
    )
    if r.status_code not in (200, 201):
        raise Exception("Workflow '" + action + "' failed on " + docname + ": " + r.text[:200])
    return r.json()


def create_order_form(customer, outlet_name, address, contact, qty, grand_total, subtotal, vat_amount):
    payload = {
        "doctype": "Order Form",
        "outlet": customer,
        "name_of_outlet": outlet_name,
        "address": address,
        "contact_number": contact,
        "fulfillment_type": "Pick-up",
        "date": "2026-03-11",
        "order_by": "Administrator",
        "mop": "Cash",
        "terms": "CASH",
        "default_terms": "CASH",
        "subtotal": subtotal,
        "vat_amount": vat_amount,
        "grand_total": grand_total,
        "table_mkaq": [{
            "doctype": "Order Details Table",
            "items": "PRD-000002",
            "qty": qty,
            "unit": "LITER",
            "price": 150.80,
            "total_price": round(qty * 150.80, 2),
            "warehouse": "WH-00001",
        }],
    }
    r = requests.post(BASE + "/api/resource/Order Form", json=payload, headers=headers)
    if r.status_code not in (200, 201):
        raise Exception("Order Form create failed: " + r.text[:300])
    name = r.json()["data"]["name"]
    print("  Created Order Form: " + name)
    return name


def approve_order(order_name):
    """Submit then Approve an Order Form."""
    print("  Submitting...")
    apply_workflow("Order Form", order_name, "Submit")
    print("  Approving...")
    apply_workflow("Order Form", order_name, "Approve")
    o = roqson.get_doc("Order Form", order_name)
    print("  Workflow state: " + str(o.get("workflow_state")))


def get_or_create_sales(order_name, customer, outlet_name, address, contact, grand_total):
    """Find existing Sales for an order, or create one directly."""
    existing = roqson.list_docs("Sales", ["name"], [["order_ref", "=", order_name]], limit=1)
    if existing:
        print("  Sales found: " + existing[0]["name"])
        return existing[0]["name"]

    payload = {
        "doctype": "Sales",
        "status": "Pending",
        "fulfillment_type": "Pick-up",
        "order_ref": order_name,
        "customer_link": customer,
        "customer_name": outlet_name,
        "address": address,
        "contact_number": contact,
        "grand_total": grand_total,
        "creation_date": "2026-03-11",
    }
    r = requests.post(BASE + "/api/resource/Sales", json=payload, headers=headers)
    if r.status_code not in (200, 201):
        raise Exception("Sales create failed: " + r.text[:300])
    name = r.json()["data"]["name"]
    requests.post(
        BASE + "/api/method/frappe.client.set_value",
        json={"doctype": "Order Form", "name": order_name, "fieldname": "sales_ref", "value": name},
        headers=headers
    )
    print("  Created Sales: " + name)
    return name


def set_sale_received(sales_name, grand_total):
    """Mark Sales as Received and initialize outstanding_balance."""
    r = requests.put(
        BASE + "/api/resource/Sales/" + sales_name,
        json={"status": "Received"},
        headers=headers
    )
    if r.status_code not in (200, 201):
        # fallback
        requests.post(
            BASE + "/api/method/frappe.client.set_value",
            json={"doctype": "Sales", "name": sales_name, "fieldname": "status", "value": "Received"},
            headers=headers
        )
    requests.post(
        BASE + "/api/method/frappe.client.set_value",
        json={"doctype": "Sales", "name": sales_name, "fieldname": "outstanding_balance", "value": grand_total},
        headers=headers
    )
    print("  Set Received, outstanding_balance=" + str(grand_total))


def create_and_submit_receipt(customer, salesman, payment_type, net_amount, apply_rows, extras=None, ref_no=None):
    """Create a Receipt and submit it."""
    payload = {
        "doctype": "Receipt",
        "date": "2026-03-11",
        "customer": customer,
        "user": "Administrator",
        "salesman": salesman,
        "payment_type": payment_type,
        "net_amount": net_amount,
        "apply_to": apply_rows,
    }
    if ref_no:
        payload["ref_no"] = ref_no
    if extras:
        payload.update(extras)

    r = requests.post(BASE + "/api/resource/Receipt", json=payload, headers=headers)
    if r.status_code not in (200, 201):
        raise Exception("Receipt create failed: " + r.text[:300])
    name = r.json()["data"]["name"]
    print("  Created Receipt: " + name)

    r2 = requests.put(BASE + "/api/resource/Receipt/" + name, json={"docstatus": 1}, headers=headers)
    if r2.status_code not in (200, 201):
        raise Exception("Receipt submit failed: " + r2.text[:300])
    print("  Submitted Receipt: " + name)
    return name


def show_sale(sales_name):
    s = roqson.get_doc("Sales", sales_name)
    print("  => " + sales_name + " | status=" + str(s.get("status")) + " | outstanding=" + str(s.get("outstanding_balance")))


# ─────────────────────────────────────────────────────────────────────────────
# BUNDLE A — Full Cash Payment
# CTMR-05130 (Orange TEST), 3 LITER @ 150.80, grand_total=506.69
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BUNDLE A -- Orange TEST -- Full Cash Payment")
print("="*60)

# Reuse Order-000319 if it already exists and is approved
bundle_a_orders = roqson.list_docs("Order Form", ["name", "workflow_state", "sales_ref"],
    [["outlet", "=", "CTMR-05130"], ["workflow_state", "=", "Approved"]], limit=1)

if bundle_a_orders:
    order_a = bundle_a_orders[0]["name"]
    print("  Reusing approved Order: " + order_a)
else:
    order_a = create_order_form("CTMR-05130", "Orange (TEST)", "Brgy. Talipapa, Quezon City",
                                "09000000001", 3, 506.69, 452.40, 54.29)
    approve_order(order_a)

sales_a = get_or_create_sales(order_a, "CTMR-05130", "Orange (TEST)",
                               "Brgy. Talipapa, Quezon City", "09000000001", 506.69)
set_sale_received(sales_a, 506.69)

receipt_a = create_and_submit_receipt(
    "CTMR-05130", "SALES-PERSON-00010", "Cash", 506.69,
    [{"doctype": "Receipt Apply To", "sales_no": sales_a, "amount_applied": 506.69}],
    ref_no="TEST-CASH-A"
)
time.sleep(2)
print("  Result (expect Completed, outstanding=0):")
show_sale(sales_a)


# ─────────────────────────────────────────────────────────────────────────────
# BUNDLE B — Two Partial Checks
# CTMR-05136 (Apple TEST), 2 LITER @ 150.80, grand_total=337.79
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BUNDLE B -- Apple TEST -- Two Partial Checks")
print("="*60)

order_b = create_order_form("CTMR-05136", "Apple (TEST)", "Brgy. Talipapa, Quezon City",
                            "09000000002", 2, 337.79, 301.60, 36.19)
approve_order(order_b)
sales_b = get_or_create_sales(order_b, "CTMR-05136", "Apple (TEST)",
                               "Brgy. Talipapa, Quezon City", "09000000002", 337.79)
set_sale_received(sales_b, 337.79)

print("  Receipt 1: partial P200 check...")
receipt_b1 = create_and_submit_receipt(
    "CTMR-05136", "SALES-PERSON-00010", "Check", 200.00,
    [{"doctype": "Receipt Apply To", "sales_no": sales_b, "amount_applied": 200.00}],
    extras={"bank": "BDO", "check_no": "CHK-TEST-001", "check_date": "2026-03-11",
            "deposit_bank_account": "CHINABANK", "deposit_date": "2026-03-12"},
    ref_no="TEST-CHK-B1"
)
time.sleep(2)
print("  After Receipt 1 (expect Received, outstanding=137.79):")
show_sale(sales_b)

print("  Receipt 2: remaining P137.79 check...")
receipt_b2 = create_and_submit_receipt(
    "CTMR-05136", "SALES-PERSON-00010", "Check", 137.79,
    [{"doctype": "Receipt Apply To", "sales_no": sales_b, "amount_applied": 137.79}],
    extras={"bank": "BDO", "check_no": "CHK-TEST-002", "check_date": "2026-03-11",
            "deposit_bank_account": "CHINABANK", "deposit_date": "2026-03-13"},
    ref_no="TEST-CHK-B2"
)
time.sleep(2)
print("  After Receipt 2 (expect Completed, outstanding=0):")
show_sale(sales_b)


# ─────────────────────────────────────────────────────────────────────────────
# BUNDLE C — Partial Bank Transfer, Balance Open
# CTMR-05137 (Yahargul TEST), 4 LITER @ 150.80, grand_total=675.58
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("BUNDLE C -- Yahargul TEST -- Partial Bank Transfer (Open)")
print("="*60)

order_c = create_order_form("CTMR-05137", "Yahargul (TEST)", "1800 Bygenwerth, Fear the Old Blood",
                            "09000000003", 4, 675.58, 603.20, 72.38)
approve_order(order_c)
sales_c = get_or_create_sales(order_c, "CTMR-05137", "Yahargul (TEST)",
                               "1800 Bygenwerth, Fear the Old Blood", "09000000003", 675.58)
set_sale_received(sales_c, 675.58)

receipt_c = create_and_submit_receipt(
    "CTMR-05137", "SALES-PERSON-00010", "Bank Transfer", 300.00,
    [{"doctype": "Receipt Apply To", "sales_no": sales_c, "amount_applied": 300.00}],
    extras={"bt_bank_account": "MBTC", "bt_ref_no": "BT-TEST-C-001"},
    ref_no="TEST-BT-C1"
)
time.sleep(2)
print("  Result (expect Received, outstanding=375.58):")
show_sale(sales_c)


# ── Fix pre-existing Received Sales outstanding balances ──────────────────────
print("\n" + "="*60)
print("Fixing pre-existing Received Sales (outstanding_balance was 0 from field add)")
print("="*60)
for sname, gt in [("Sales-000012", 506.69), ("Sales-000013", 337.79), ("Sales-000014", 337.79)]:
    requests.post(
        BASE + "/api/method/frappe.client.set_value",
        json={"doctype": "Sales", "name": sname, "fieldname": "outstanding_balance", "value": gt},
        headers=headers
    )
    print("  " + sname + " -> outstanding_balance=" + str(gt))


# ── Summary ───────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print("SUMMARY")
print("="*60)
print("Bundle A (Full Cash):")
print("  Order=" + order_a + "  Sales=" + sales_a + "  Receipt=" + receipt_a)
print()
print("Bundle B (Two Partial Checks):")
print("  Order=" + order_b + "  Sales=" + sales_b)
print("  Receipt1=" + receipt_b1 + "  Receipt2=" + receipt_b2)
print()
print("Bundle C (Partial BT, Open Balance):")
print("  Order=" + order_c + "  Sales=" + sales_c + "  Receipt=" + receipt_c)
print()
print("Done.")
