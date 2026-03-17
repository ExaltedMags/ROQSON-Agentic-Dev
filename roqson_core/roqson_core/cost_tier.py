import frappe

# Cost Tier DocType Event handlers — populated in Phase 5.2.


def before_save(doc, method):
    # Ported from Server Script: "Cost Tier: Display Name"
    status_label = "Current" if doc.status == "Active" else "Legacy"
    doc.display_name = f"₱{doc.unit_cost} ({status_label}) — {int(doc.remaining_quantity)} units"
