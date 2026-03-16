"""
Step 4 — Update Sales DocType and remove Completed gate
Sub-steps:
  4A. Add outstanding_balance, sec_receipts, receipts_html fields to Sales DocType
  4B. Remove status/before_save Completed gate from Sales: Paid Validation
  4C. Snapshot after changes
"""

import roqson
import requests
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": "token " + key + ":" + secret}
BASE = "https://roqson-industrial-sales.s.frappe.cloud"


# ─────────────────────────────────────────────────────────────────────────────
# 4A — Add fields to Sales DocType
# ─────────────────────────────────────────────────────────────────────────────

print("4A: Fetching Sales DocType...")
sales_dt = roqson.get_doc("DocType", "Sales")
fields = sales_dt.get("fields", [])

# Guard: check which new fields already exist
existing_fieldnames = {f.get("fieldname") for f in fields}
NEW_FIELDNAMES = ["outstanding_balance", "sec_receipts", "receipts_html"]
already_exists = [fn for fn in NEW_FIELDNAMES if fn in existing_fieldnames]

if already_exists:
    print("Fields already exist — skipping 4A: " + str(already_exists))
else:
    # Find insertion point: after grand_total
    idx_gt = next((i for i, f in enumerate(fields) if f.get("fieldname") == "grand_total"), None)
    if idx_gt is None:
        # Fallback: append at end
        idx_insert = len(fields)
        print("grand_total not found — appending at end")
    else:
        idx_insert = idx_gt + 1
        print("Inserting after grand_total at index " + str(idx_insert))

    new_fields = [
        {
            "fieldname": "outstanding_balance",
            "label": "Outstanding Balance",
            "fieldtype": "Currency",
            "read_only": 1,
            "doctype": "DocField",
        },
        {
            "fieldname": "sec_receipts",
            "label": "Receipts",
            "fieldtype": "Section Break",
            "doctype": "DocField",
        },
        {
            "fieldname": "receipts_html",
            "label": "Receipts",
            "fieldtype": "HTML",
            "read_only": 1,
            "doctype": "DocField",
        },
    ]

    # Insert and re-index
    for offset, nf in enumerate(new_fields):
        fields.insert(idx_insert + offset, nf)
    for i, f in enumerate(fields):
        f["idx"] = i + 1

    sales_dt["fields"] = fields

    # Add field-level permission for Sales role on outstanding_balance
    perms = sales_dt.get("field_order") or []

    r = requests.put(BASE + "/api/resource/DocType/Sales", json=sales_dt, headers=headers)
    print("Sales DocType update: " + str(r.status_code))
    if r.status_code not in (200, 201):
        print(r.text[:500])
        raise Exception("Failed to update Sales DocType")

    # Verify new fields exist
    updated = roqson.get_doc("DocType", "Sales")
    updated_names = {f.get("fieldname") for f in updated.get("fields", [])}
    for fn in NEW_FIELDNAMES:
        status = "OK" if fn in updated_names else "MISSING"
        print("  Field " + fn + ": " + status)


# ─────────────────────────────────────────────────────────────────────────────
# 4B — Remove Completed gate from Sales: Paid Validation
# ─────────────────────────────────────────────────────────────────────────────

SCRIPT_NAME = "Sales: Paid Validation"
print("\n4B: Reading " + SCRIPT_NAME + "...")

current_script = roqson.get_script_body("Client Script", SCRIPT_NAME)
print("Current script length: " + str(len(current_script)) + " chars")

# The new script keeps refresh (pick-up button) but replaces status + before_save
new_script = """// Sales Form Script

frappe.ui.form.on('Sales', {

    // status and before_save Completed gates removed 2026-03-11.
    // Completed status is now set automatically by Receipt server script on submit.

    refresh: function(frm) {
        var roles = frappe.user_roles;
        var can_confirm = roles.includes('Administrator') || roles.includes('System Manager') || roles.includes('Warehouse') || roles.includes('Manager');
        if (frm.doc.fulfillment_type === 'Pick-up' && frm.doc.status === 'Pending' && can_confirm) {
            frm.page.add_inner_button('Confirm Pick-up', function() {
                frappe.confirm('Has the customer collected these items?', function() {
                    frm.set_value('status', 'Received');
                    frm.save();
                });
            }).addClass('btn-primary').css({'color': 'white', 'background-color': '#166534'});
        }
    },

});
"""

# Show diff before applying
print("\nProposed change to " + SCRIPT_NAME + ":")
from difflib import unified_diff
old_lines = current_script.splitlines(keepends=True)
new_lines = new_script.splitlines(keepends=True)
diff = list(unified_diff(old_lines, new_lines, fromfile=SCRIPT_NAME + " (current)", tofile=SCRIPT_NAME + " (proposed)"))
if diff:
    print("".join(diff))
else:
    print("(no diff — script may already be updated)")

# Check if gate is present in current script
has_gate = ("Completed gate" not in current_script and
            ("status === 'Completed'" in current_script or "status == 'Completed'" in current_script))

if not has_gate and "Completed gates removed" in current_script:
    print("\n[SKIP] Gate already removed from " + SCRIPT_NAME)
else:
    confirm = input("\nApply this change to '" + SCRIPT_NAME + "'? [y/N]: ").strip().lower()
    if confirm != "y":
        print("[CANCELLED] No changes written.")
    else:
        roqson.update_doc("Client Script", SCRIPT_NAME, {"script": new_script})

        # Verify
        verified = roqson.get_script_body("Client Script", SCRIPT_NAME)
        if "status === 'Completed'" not in verified and "status == 'Completed'" not in verified:
            print("[OK] Completed gate successfully removed from " + SCRIPT_NAME)
        else:
            print("[WARNING] Gate may still be present — verify manually")


# ─────────────────────────────────────────────────────────────────────────────
# 4C — Snapshot after changes
# ─────────────────────────────────────────────────────────────────────────────
print("\n4C: Taking post-change snapshot...")
roqson.snapshot_scripts("Sales", "snapshot_sales_after_receipts.json")
print("Snapshot saved to snapshot_sales_after_receipts.json")
print("\nAll Step 4 operations complete.")
