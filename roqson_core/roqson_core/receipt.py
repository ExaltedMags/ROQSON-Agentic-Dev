import frappe

# Receipt DocType Event handlers — populated in Phase 5.1.
# 2 scripts to port (see ARCHITECTURE.md § receipt.py).


def before_cancel(doc, method):
    # Ported from: "Receipt: Revert Sales on Cancel"
    pass


def on_submit(doc, method):
    # Ported from: "Receipt: Update Sales on Submit"
    pass
