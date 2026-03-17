import frappe

# Trips DocType Event handlers — populated in Phase 5.9.
# 8 scripts to port (see ARCHITECTURE.md § trips.py).


def before_insert(doc, method):
    # Ported from Server Script: "Trip Numbering"
    if not doc.trip_no or doc.trip_no == "0" or doc.get("__islocal"):
        today = doc.date or frappe.utils.today()
        count = frappe.db.count("Trips", filters={
            "date": today,
            "name": ["!=", doc.name or ""]
        })
        doc.trip_no = str(count + 1).zfill(4)


def before_validate(doc, method):
    # Ported from Server Script: "Fix Dispatch Time"
    db_val = frappe.db.get_value("Trips", doc.name, "dispatch_time")
    if db_val and doc.dispatch_time:
        old_segs = str(db_val).split(":")
        old_segs[0] = old_segs[0].zfill(2)
        old_segs[-1] = old_segs[-1].split(".")[0].zfill(2)
        old_padded = ":".join(old_segs[:3])

        new_segs = str(doc.dispatch_time).split(":")
        new_segs[0] = new_segs[0].zfill(2)
        new_segs[-1] = new_segs[-1].split(".")[0].zfill(2)
        new_padded = ":".join(new_segs[:3])

        if old_padded != new_padded:
            frappe.throw("Value cannot be changed for Dispatch Time")

        doc.dispatch_time = old_padded


def before_save(doc, method):
    _enforce_eligibility(doc)
    _multi_driver_sync(doc)
    _transit_update(doc)
    _delivery_status_notification(doc)


def _enforce_eligibility(doc):
    # Ported from Server Script: "Enforce Eligibility"
    CHILD_TABLE_FIELD = "table_cpme"
    rows = doc.get(CHILD_TABLE_FIELD) or []

    if not rows or not rows[0].get("sales_no"):
        frappe.throw("Row 1 must have a Sales No. before saving.")

    current_trip_sales = {}
    if not doc.is_new():
        existing_rows = frappe.get_all(
            "Trips Table",
            filters={"parent": doc.name},
            fields=["sales_no"],
            limit_page_length=500
        )
        for r in existing_rows:
            if r.get("sales_no"):
                current_trip_sales[r.get("sales_no")] = 1

    first_sales_name = rows[0].get("sales_no")
    first_sales = frappe.db.get_value(
        "Sales", first_sales_name,
        ["status", "customer_link", "address", "contact_number"], as_dict=True
    ) or {}

    if not first_sales:
        frappe.throw("Sales record " + str(first_sales_name) + " not found.")

    status = first_sales.get("status")
    if status != "Pending" and not current_trip_sales.get(first_sales_name):
        frappe.throw(
            "Sales record " + str(first_sales_name) + " is not eligible (status must be Pending, got " + str(status) + ")."
        )

    first_outlet = first_sales.get("customer_link")
    if not first_outlet:
        frappe.throw("Sales record " + str(first_sales_name) + " has no customer. Cannot create Trips.")

    doc.set("outlet", first_outlet)
    doc.set("contact_number", first_sales.get("contact_number") or "")
    doc.set("address", first_sales.get("address") or "")

    seen = {}
    for r in rows:
        sales_name = r.get("sales_no")
        if not sales_name:
            continue
        if sales_name in seen:
            frappe.throw("Duplicate Sales record in Trips: " + str(sales_name))
        seen[sales_name] = 1

        vals = frappe.db.get_value("Sales", sales_name, ["status", "customer_link"], as_dict=True) or {}
        outlet = vals.get("customer_link")
        st = vals.get("status")

        if not outlet:
            frappe.throw("Sales record " + str(sales_name) + " has no customer.")
        if outlet != first_outlet:
            frappe.throw(
                "Sales record " + str(sales_name) + " belongs to outlet '" + str(outlet) +
                "', but Trips is locked to '" + str(first_outlet) + "'."
            )
        if st != "Pending" and not current_trip_sales.get(sales_name):
            frappe.throw(
                "Sales record " + str(sales_name) + " is not eligible (status must be Pending, got " + str(st) + ")."
            )


def _multi_driver_sync(doc):
    # Ported from Server Script: "Trip Ticket Multi-Driver Sync"
    SALES_TABLE_FIELD = "table_cpme"
    ITEM_TABLE_FIELD = "delivery_items"
    DRIVER_TABLE_FIELD = "driver_assignments"

    sales_rows = doc.get(SALES_TABLE_FIELD) or []
    if not sales_rows:
        frappe.throw("Add at least one Sales row before saving the Trips.")

    distinct_sales = []
    sales_seen = {}
    current_trip_sales = {}

    if not doc.is_new():
        existing_rows = frappe.get_all("Trips Table", filters={"parent": doc.name}, fields=["sales_no"], limit_page_length=500)
        for r in existing_rows:
            if r.get("sales_no"):
                current_trip_sales[r.get("sales_no")] = 1

    for row in sales_rows:
        sales_no = row.get("sales_no")
        if not sales_no:
            frappe.throw("Every Sales row must have a Sales No.")
        if not sales_seen.get(sales_no):
            sales_seen[sales_no] = 1
            distinct_sales.append(sales_no)

    first_sales = frappe.db.get_value(
        "Sales", distinct_sales[0],
        ["status", "customer_link", "address", "contact_number", "order_ref"], as_dict=True
    ) or {}
    if not first_sales:
        frappe.throw("Sales record " + str(distinct_sales[0]) + " not found.")

    first_outlet = first_sales.get("customer_link")
    if not first_outlet:
        frappe.throw("Sales record " + str(distinct_sales[0]) + " has no customer.")

    doc.set("outlet", first_outlet)
    doc.set("contact_number", first_sales.get("contact_number") or "")
    doc.set("address", first_sales.get("address") or "")

    if first_sales.get("order_ref"):
        contact_person = frappe.db.get_value("Order Form", first_sales.get("order_ref"), "contact_person") or ""
        if contact_person:
            doc.set("contact_person", contact_person)

    # Preserve split rows
    existing_splits = {}
    for row in doc.get(ITEM_TABLE_FIELD) or []:
        key = str(row.get("sales_item_row") or "") + "::" + str(row.get("sales_no") or "") + "::" + str(row.get("item_code") or "")
        if key not in existing_splits:
            existing_splits[key] = []
        existing_splits[key].append({
            "assigned_driver": row.get("assigned_driver") or "",
            "delivered": row.get("delivered") or 0,
            "quantity": row.get("quantity") or 0,
            "liters_per_unit": row.get("liters_per_unit") or 0,
            "total_liters": row.get("total_liters") or 0
        })

    doc.set(ITEM_TABLE_FIELD, [])
    total_qty = 0.0
    total_liters = 0.0

    for sales_no in distinct_sales:
        sales_doc = frappe.get_doc("Sales", sales_no)
        order_ref = sales_doc.get("order_ref") or ""
        for item in sales_doc.get("items") or []:
            item_code = item.get("item") or ""
            item_qty = item.get("qty") or 0
            liters_per_unit = frappe.db.get_value("Product", item_code, "custom_liters") or 0
            key = str(item.get("name") or "") + "::" + str(sales_no) + "::" + str(item_code)
            splits = existing_splits.get(key) or []

            if len(splits) > 1:
                total_split_qty = sum(float(s.get("quantity") or 0) for s in splits)
                if total_split_qty > float(item_qty or 0):
                    frappe.throw(
                        "Split quantities for " + str(item_code) + " (" + str(total_split_qty) +
                        ") exceed the ordered quantity (" + str(item_qty) + "). Please correct before saving."
                    )
                for split in splits:
                    split_qty = float(split.get("quantity") or 0)
                    split_liters = split_qty * float(liters_per_unit or 0)
                    child = doc.append(ITEM_TABLE_FIELD, {})
                    child.sales_no = sales_no
                    child.order_no = order_ref
                    child.sales_item_row = item.get("name") or ""
                    child.item_code = item_code
                    child.item_name = item_code
                    child.quantity = split_qty
                    child.liters_per_unit = liters_per_unit
                    child.total_liters = split_liters
                    child.assigned_driver = split.get("assigned_driver") or ""
                    child.delivered = split.get("delivered") or 0
                    total_qty += split_qty
                    total_liters += split_liters
            else:
                previous = splits[0] if splits else {}
                total_line_liters = float(item_qty or 0) * float(liters_per_unit or 0)
                child = doc.append(ITEM_TABLE_FIELD, {})
                child.sales_no = sales_no
                child.order_no = order_ref
                child.sales_item_row = item.get("name") or ""
                child.item_code = item_code
                child.item_name = item_code
                child.quantity = item_qty
                child.liters_per_unit = liters_per_unit
                child.total_liters = total_line_liters
                child.assigned_driver = previous.get("assigned_driver") or ""
                child.delivered = previous.get("delivered") or 0
                total_qty += float(item_qty or 0)
                total_liters += float(total_line_liters or 0)

    customer = frappe.db.get_value("Customer Information", first_outlet, ["business_address", "residential_address"], as_dict=True) or {}
    ph_address_name = customer.get("business_address") or customer.get("residential_address") or ""
    ph_address = {}
    if ph_address_name:
        ph_address = frappe.db.get_value("PH Address", ph_address_name, ["custom_barangay", "custom_zip_code"], as_dict=True) or {}

    doc.set("area_barangay", ph_address.get("custom_barangay") or "")
    doc.set("area_zip_code", ph_address.get("custom_zip_code") or "")
    doc.set("sales_numbers_display", ", ".join(distinct_sales))
    doc.set("total_item_qty", total_qty)
    doc.set("total_liters", total_liters)

    for sales_no in distinct_sales:
        frappe.db.set_value("Sales", sales_no, "trip_ticket", doc.name)

    assignment_rows = doc.get(DRIVER_TABLE_FIELD) or []
    item_rows = doc.get(ITEM_TABLE_FIELD) or []

    driver_counts = {}
    driver_map = {}
    total_pending = 0
    total_unassigned = 0

    for item_row in item_rows:
        if not item_row.get("delivered"):
            total_pending += 1
        if not item_row.get("assigned_driver"):
            total_unassigned += 1
        else:
            ad = item_row.get("assigned_driver")
            driver_counts[ad] = driver_counts.get(ad, 0) + 1

    for drow in assignment_rows:
        if drow.get("driver"):
            driver_map[drow.get("driver")] = 1

    for item_row in item_rows:
        ad = item_row.get("assigned_driver")
        if ad and not driver_map.get(ad):
            frappe.throw("Assigned Driver " + str(ad) + " is missing from Driver Assignment table.")

    all_drivers_completed = 1
    active_drivers_with_items = 0
    driver_names = []

    for drow in assignment_rows:
        driver_name = drow.get("driver")
        if not driver_name:
            continue
        full_name = frappe.db.get_value("Driver", driver_name, "full_name") or driver_name
        driver_names.append(full_name)
        assigned_count = driver_counts.get(driver_name, 0)
        drow.assigned_items = str(assigned_count) + " item(s)"

        if assigned_count > 0:
            active_drivers_with_items += 1

        if drow.get("proof_of_delivery") and not drow.get("proof_time_stamp"):
            drow.proof_time_stamp = frappe.utils.now_datetime()
        if not drow.get("proof_of_delivery"):
            drow.proof_time_stamp = None

        if drow.get("submitted"):
            has_pod = drow.get("proof_of_delivery") or doc.get("proof_of_delivery")
            if not has_pod:
                frappe.throw("Driver " + str(full_name) + " must upload proof of delivery before submitting.")
            driver_pending = sum(
                1 for r in item_rows
                if r.get("assigned_driver") == driver_name and not r.get("delivered")
            )
            if driver_pending > 0:
                frappe.throw("Driver " + str(full_name) + " has " + str(driver_pending) + " items not checked off.")
            if not drow.get("submitted_at"):
                drow.submitted_at = frappe.utils.now_datetime()
            if not drow.get("submitted_by"):
                drow.submitted_by = frappe.session.user
        else:
            if assigned_count > 0:
                driver_pending = sum(
                    1 for r in item_rows
                    if r.get("assigned_driver") == driver_name and not r.get("delivered")
                )
                if driver_pending == 0 and doc.get("delivery_status") == "Successful":
                    drow.submitted = 1
                    drow.submitted_at = frappe.utils.now_datetime()
                    drow.submitted_by = frappe.session.user
                else:
                    all_drivers_completed = 0
                    drow.submitted_at = None
                    drow.submitted_by = ""

    if active_drivers_with_items == 0 and len(item_rows) > 0:
        all_drivers_completed = 0

    doc.set("assigned_drivers_display", ", ".join(driver_names))
    doc.set("all_drivers_completed", all_drivers_completed)

    legacy_final_state = (doc.get("workflow_state") or "") in ["Received", "Completed", "Failed"]

    if doc.get("delivery_status") == "Successful":
        if total_pending > 0:
            frappe.throw("All " + str(total_pending) + " items must be checked off as Delivered before marking as Successful.")
        if total_unassigned > 0:
            frappe.throw("All " + str(total_unassigned) + " items must be assigned to a driver before completion.")
        if not all_drivers_completed and not legacy_final_state:
            frappe.throw("All assigned drivers must submit their delivery records before completion.")

    if all_drivers_completed and active_drivers_with_items > 0:
        doc.set("delivery_status", "Successful")


def _transit_update(doc):
    # Ported from Server Script: "Trip Ticket Transit Update"
    old = doc.get_doc_before_save()
    old_wf = (old.get("workflow_state") or "") if old else ""
    new_wf = (doc.get("workflow_state") or "")

    if new_wf == "In Transit" and old_wf != "In Transit":
        if not doc.dispatch_time:
            doc.dispatch_time = frappe.utils.now_datetime().strftime("%H:%M:%S")
        for row in (doc.table_cpme or []):
            if row.sales_no:
                if frappe.db.get_value("Sales", row.sales_no, "status") == "Dispatching":
                    frappe.db.set_value("Sales", row.sales_no, "status", "In Transit")

    if new_wf == "Cancelled" and old_wf != "Cancelled":
        for row in (doc.table_cpme or []):
            if row.sales_no:
                frappe.db.set_value("Sales", row.sales_no, {"status": "Pending", "trip_ticket": ""})

    if new_wf == "Completed" and old_wf != "Completed":
        for row in (doc.table_cpme or []):
            if row.sales_no:
                frappe.db.set_value("Sales", row.sales_no, "status", "Received")

    if new_wf == "Failed" and old_wf != "Failed":
        for row in (doc.table_cpme or []):
            if row.sales_no:
                frappe.db.set_value("Sales", row.sales_no, "status", "Failed")


def _delivery_status_notification(doc):
    # Ported from Server Script: "Delivery Status Notification"
    old = doc.get_doc_before_save()
    old_completed = (old.get("all_drivers_completed") or 0) if old else 0

    if not (doc.get("all_drivers_completed") and not old_completed):
        return

    recipients = {}
    sales_list = []
    driver_names = []

    for drow in (doc.get("driver_assignments") or []):
        if drow.get("driver"):
            driver_names.append(frappe.db.get_value("Driver", drow.get("driver"), "full_name") or drow.get("driver"))

    customer = ""
    for row in (doc.get("table_cpme") or []):
        sales_no = row.get("sales_no")
        if not sales_no:
            continue
        sales_list.append(sales_no)
        sales_doc = frappe.db.get_value("Sales", sales_no, ["customer_name", "owner"], as_dict=True) or {}
        if not customer:
            customer = sales_doc.get("customer_name") or ""
        if sales_doc.get("owner"):
            recipients[sales_doc.get("owner")] = 1
        if row.get("order_no"):
            dsp = frappe.db.get_value("Order Form", row.get("order_no"), "owner")
            if dsp:
                recipients[dsp] = 1

    message = "Delivery completed - " + ", ".join(sales_list)
    if customer:
        message += " | " + customer
    if doc.get("address"):
        message += " | " + doc.get("address")
    if driver_names:
        message += " | Delivered by: " + ", ".join(driver_names)

    for user in recipients:
        if user and user != "Guest":
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "subject": "Delivery completed",
                "email_content": message,
                "document_type": "Trips",
                "document_name": doc.name
            }).insert(ignore_permissions=True)


def after_insert(doc, method):
    # Ported from Server Script: "Trip Ticket Creation Notification"
    def get_enabled_users_with_role(role_name):
        users = frappe.get_all("Has Role", filters={"role": role_name}, pluck="parent")
        if not users:
            return []
        return frappe.get_all("User", filters={"name": ["in", users], "enabled": 1}, pluck="name")

    stock_managers = get_enabled_users_with_role("Stock Manager")
    if stock_managers:
        sales_count = len(doc.table_cpme) if doc.table_cpme else 0
        sched_date = doc.date or "TBD"
        cust_name = doc.outlet or "Unknown"
        msg = f"New Trips created — {doc.name} | {cust_name} | {sales_count} sale(s) | Scheduled: {sched_date}"
        for sm in stock_managers:
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": sm,
                "type": "Alert",
                "subject": "New Trips",
                "email_content": msg,
                "document_type": "Trips",
                "document_name": doc.name
            }).insert(ignore_permissions=True)


def after_save(doc, method):
    # Ported from Server Script: "Trip Ticket and Order Form Traceability"
    table_field = "table_cpme"
    sales_names = {}
    for row in (doc.get(table_field) or []):
        if row.get("order_no"):
            frappe.db.set_value("Order Form", row.get("order_no"), "trip_ticket", doc.name)
        if row.get("sales_no"):
            sales_name = row.get("sales_no")
            sales_names[sales_name] = 1
            frappe.db.set_value("Sales", sales_name, "trip_ticket", doc.name)
            if frappe.db.get_value("Sales", sales_name, "status") == "Pending":
                frappe.db.set_value("Sales", sales_name, "status", "Dispatching")

    old = doc.get_doc_before_save()
    if old:
        for old_row in (old.get(table_field) or []):
            old_sales = old_row.get("sales_no")
            if old_sales and not sales_names.get(old_sales):
                if frappe.db.get_value("Sales", old_sales, "trip_ticket") == doc.name:
                    frappe.db.set_value("Sales", old_sales, "trip_ticket", "")
