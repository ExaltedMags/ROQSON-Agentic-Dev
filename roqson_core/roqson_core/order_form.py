import frappe

# Order Form DocType Event handlers — populated in Phase 5.10.
# 20 scripts to port (see ARCHITECTURE.md § order_form.py).
#
# Events: before_delete, before_save (9 merged), before_submit,
#         after_save, on_update_after_submit (3 merged),
#         on_submit (2 merged), on_cancel (2 merged)


def before_delete(doc, method):
    # Ported from: "Auto-close PCRs on Order Delete (DocType Event)"
    pass


def before_save(doc, method):
    # Merged from (in order):
    # - "MOP Cash Terms Bypass"
    # - "Order Form Admin Edit Bypass"
    # - "Allow Delivery Address Edit for Admin"
    # - "Price Edit"
    # - "Price Modified Flag"
    # - "Auto-fill Approved By"
    # - "Validate Term Request Change"
    # - "Notes Acknowledgment Validation"
    pass


def before_submit(doc, method):
    # Ported from: "Reservation cannot exceed available"
    pass


def after_save(doc, method):
    # Merged from:
    # - "Auto Approve"
    # - "Price Change Request Creator"
    pass


def on_update_after_submit(doc, method):
    # Merged from:
    # - "Auto Create Sales on Approval"
    # - "Approved, Rejected, Reserved, Dispatched, Delivered, Delivery Failed, Rescheduled"
    # - "Auto Cancel Sales on Order Cancellation"
    # - "Inventory Stock Out"
    pass


def on_submit(doc, method):
    # Merged from:
    # - "Order Form Stock Notiffication"
    # - "Order Submitted Notification"
    pass


def on_cancel(doc, method):
    # Merged from:
    # - "Order Canceled Notification"
    # - "Inventory Stock Canceled"
    pass
