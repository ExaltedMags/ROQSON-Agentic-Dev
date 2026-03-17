import frappe

# Sales DocType Event handlers — populated in Phase 5.6.
# 2 scripts to port (see ARCHITECTURE.md § sales.py).


def before_save(doc, method):
    # Ported from: "Auto Cancel Order on Sales Cancellation"
    pass


def after_save(doc, method):
    # Ported from: "Sales Inventory Stock Out"
    pass
