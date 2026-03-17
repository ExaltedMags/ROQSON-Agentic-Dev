import frappe


def before_delete(doc, method):
    # Ported from Server Script: "Auto-close PCRs on Order Delete (DocType Event)"
    pending = frappe.get_all("Price Change Request",
        filters={"order_form": doc.name, "status": "Pending"},
        fields=["name"])
    for pcr in pending:
        frappe.db.set_value("Price Change Request", pcr.name, {
            "status": "Rejected",
            "remarks": "Auto-closed: order was deleted",
            "review_date": frappe.utils.now()
        })


def before_save(doc, method):
    # Merged from (in order): MOP Cash Terms Bypass, Order Form Admin Edit Bypass,
    # Allow Delivery Address Edit for Admin, Price Edit, Price Modified Flag,
    # Auto-fill Approved By, Validate Term Request Change, Notes Acknowledgment Validation

    # --- MOP Cash Terms Bypass ---
    if doc.mop == "Cash":
        doc.terms = ""
        doc.flags.ignore_mandatory = True

    # --- Order Form Admin Edit Bypass ---
    admin_bypass_roles = ["Administrator", "Manager", "System Manager", "President"]
    user_roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, pluck="role")
    user_roles_list = list(user_roles)
    has_admin_role = any(r in user_roles_list for r in admin_bypass_roles)
    if has_admin_role:
        doc.flags.ignore_validate_update_after_submit = True

    # --- Allow Delivery Address Edit for Admin ---
    if doc.docstatus == 1:
        allowed_addr_roles = ["Manager", "President", "Administrator", "System Manager",
                              "Sales", "Sales Manager", "Sales User"]
        valid_states = ["Draft", "Needs Review", "Approved", "Reserved"]
        if any(r in user_roles_list for r in allowed_addr_roles) and doc.workflow_state in valid_states:
            doc.flags.ignore_validate_update_after_submit = True

    # --- Price Edit ---
    if not doc.is_new():
        try:
            old_doc = frappe.get_doc(doc.doctype, doc.name)
        except frappe.DoesNotExistError:
            old_doc = None

        if old_doc:
            price_changed = False
            for i, row in enumerate(doc.get("table_mkaq", [])):
                old_price = 0
                matched = False
                if row.name:
                    for old_row in old_doc.get("table_mkaq", []):
                        if old_row.name == row.name:
                            old_price = old_row.price
                            matched = True
                            break
                if not matched and i < len(old_doc.get("table_mkaq", [])):
                    old_price = old_doc.get("table_mkaq", [])[i].price
                if abs(frappe.utils.flt(row.price) - frappe.utils.flt(old_price)) > 0.001:
                    price_changed = True
                    break

            if price_changed:
                price_edit_roles = ["Administrator", "Manager", "System Manager", "President"]
                role_records = frappe.db.get_all("Has Role",
                    filters={"parent": frappe.session.user, "parenttype": "User"}, pluck="role")
                is_admin = any(r in role_records for r in price_edit_roles)
                state = doc.workflow_state
                is_draft = not state or state == "Draft"
                if not is_draft and not is_admin:
                    frappe.throw("Only Managers/Presidents can change the price after the order has moved beyond Draft.")

    # --- Price Modified Flag ---
    price_changed = False
    for row in (doc.table_mkaq or []):
        if row.items:
            base_price = frappe.db.get_value("Product", row.items, "sales_price")
            if base_price is not None and row.price < base_price:
                price_changed = True
                break
    doc.price_modified = 1 if price_changed else 0

    # --- Auto-fill Approved By ---
    if doc.get("workflow_state") == "Approved" and not doc.get("approved_by"):
        user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
        doc.approved_by = user_name

    # --- Validate Term Request Change ---
    if doc.requested_term and doc.default_terms:
        if doc.requested_term.strip() == doc.default_terms.strip():
            frappe.throw(
                "Requested Term cannot be the same as the customer's default term (" +
                str(doc.default_terms) + "). Please select a different term or leave it blank."
            )

    # --- Notes Acknowledgment Validation ---
    def _is_pure_dsp():
        exempt_roles = ["Manager", "President", "Administrator", "Purchaser", "System Manager", "Sales"]
        dsp_roles = frappe.db.get_all("Has Role", filters={"parent": frappe.session.user}, pluck="role")
        if any(r in exempt_roles for r in dsp_roles):
            return False
        return "DSP" in dsp_roles

    def _parse_note_items(html):
        if not html or not html.strip():
            return []
        def extract_text(raw):
            text = ""
            in_tag = False
            for ch in raw:
                if ch == "<":
                    in_tag = True
                elif ch == ">" and in_tag:
                    in_tag = False
                elif not in_tag:
                    text += ch
            return text.strip()
        def extract_tag_contents(html_str, tag):
            lower = html_str.lower()
            o_tag, c_tag = "<" + tag, "</" + tag + ">"
            start = 0
            while True:
                t_open = lower.find(o_tag, start)
                if t_open == -1:
                    break
                t_gt = lower.find(">", t_open)
                t_close = lower.find(c_tag, t_gt)
                if t_gt == -1 or t_close == -1:
                    break
                yield html_str[t_gt + 1: t_close]
                start = t_close + len(c_tag)
        items = [extract_text(i) for i in extract_tag_contents(html, "li") if extract_text(i)]
        if not items:
            items = [extract_text(i) for i in extract_tag_contents(html, "p") if extract_text(i)]
        return items

    if _is_pure_dsp():
        notes_html = doc.get("internal_notes") or ""
        note_items = _parse_note_items(notes_html)
        if note_items:
            ack_raw = doc.get("notes_acknowledgments") or "{}"
            try:
                ack_data = frappe.parse_json(ack_raw)
            except Exception:
                ack_data = {}
            unacked_count = sum(1 for idx in range(len(note_items)) if not ack_data.get("item_" + str(idx)))
            if unacked_count > 0:
                frappe.throw(
                    "Acknowledgment Required: As a DSP, you must acknowledge all " + str(unacked_count) +
                    " note items before saving. Please check the boxes on the Notes tab."
                )


def before_submit(doc, method):
    # Ported from Server Script: "Reservation cannot exceed available"
    if doc.workflow_state == "Delivered":
        for row in (doc.table_mkaq or []):
            if not row.product:
                continue
            reserved = frappe.db.sql("""
                SELECT
                    COALESCE(SUM(CASE WHEN l.movement_type='Reserved' THEN t.qty ELSE 0 END),0)
                    - COALESCE(SUM(CASE WHEN l.movement_type='Out' THEN t.qty ELSE 0 END),0)
                FROM `tabInventory Ledger` l
                JOIN `tabInventory Ledger Table` t ON t.parent = l.name
                WHERE l.order_no = %s AND t.product = %s
            """, (doc.name, row.product))[0][0] or 0

            if float(row.qty or 0) > float(reserved):
                frappe.throw(
                    "Cannot deliver " + str(row.product) + ". "
                    "Reserved remaining: " + str(reserved) + ", Attempted: " + str(row.qty or 0)
                )


def after_save(doc, method):
    # Merged from: "Auto Approve" + "Price Change Request Creator"

    # --- Auto Approve ---
    if doc.get("workflow_state") == "Needs Review":
        price_rows_ok = all(
            not (row.get("items") and not row.get("is_promo_reward") and
                 (frappe.db.get_value("Product", row.get("items"), "sales_price") or 0) > 0 and
                 row.get("price", 0) < (frappe.db.get_value("Product", row.get("items"), "sales_price") or 0))
            for row in (doc.get("table_mkaq") or [])
        )
        terms = (doc.get("terms") or "").strip()
        default_terms = (doc.get("default_terms") or "").strip()
        terms_ok = (terms == default_terms)
        terms_rows_ok = all(
            not ((row.get("terms_child") or "").strip() and
                 (row.get("terms_child") or "").strip() != default_terms)
            for row in (doc.get("table_aaaa") or [])
        )

        if terms_ok and price_rows_ok and terms_rows_ok:
            user_name = frappe.db.get_value("User", frappe.session.user, "full_name") or frappe.session.user
            frappe.db.set_value("Order Form", doc.name, {
                "workflow_state": "Approved",
                "docstatus": 1,
                "approved_by": user_name
            }, update_modified=False)

            existing = frappe.get_all("Sales", filters={"order_ref": doc.name}, limit=1)
            if existing:
                if not doc.get("sales_ref"):
                    frappe.db.set_value("Order Form", doc.name, "sales_ref",
                                        existing[0].name, update_modified=False)
            else:
                items = [
                    {
                        "doctype": "Sales Items Table",
                        "item": row.get("items"),
                        "qty": row.get("qty") or 0,
                        "unit": row.get("unit") or "",
                        "unit_price": row.get("price") or 0,
                        "total": row.get("total_price") or 0,
                        "warehouse": row.get("warehouse") or "",
                        "is_promo": row.get("is_promo_reward") or 0,
                    }
                    for row in (doc.get("table_mkaq") or []) if row.get("items")
                ]
                sales = frappe.get_doc({
                    "doctype": "Sales",
                    "status": "Pending",
                    "fulfillment_type": doc.get("fulfillment_type") or "Delivery",
                    "order_ref": doc.name,
                    "customer_link": doc.get("outlet") or "",
                    "customer_name": doc.get("name_of_outlet") or doc.get("outlet") or "",
                    "address": doc.get("address") or "",
                    "contact_number": doc.get("contact_number") or "",
                    "grand_total": doc.get("grand_total") or 0,
                    "creation_date": frappe.utils.nowdate(),
                    "items": items,
                })
                sales.insert(ignore_permissions=True)
                frappe.db.set_value("Order Form", doc.name, "sales_ref", sales.name, update_modified=False)

    # --- Price Change Request Creator ---
    if doc.apply_promo:
        promo = frappe.get_doc("Promos", doc.apply_promo)
        eligible_qty = sum(
            row.qty or 0
            for row in (doc.table_mkaq or [])
            if row.items == promo.buy_item and not row.is_promo_reward
        )
        if eligible_qty < promo.buy_quantity:
            frappe.throw(
                "Promo <b>" + str(doc.apply_promo) + "</b> requires " + str(promo.buy_quantity) +
                "x " + str(promo.buy_item) + " but it is no longer in the order. "
                "Remove the promo or add the item back."
            )

    for row in (doc.table_mkaq or []):
        if row.items and not row.is_promo_reward:
            base_price = frappe.db.get_value("Product", row.items, "sales_price")
            if base_price is not None and row.price < base_price:
                existing = frappe.db.exists("Price Change Request", {
                    "order_form": doc.name,
                    "item": row.items,
                    "new_price": row.price,
                    "status": "Pending"
                })
                if not existing:
                    pcr = frappe.new_doc("Price Change Request")
                    pcr.naming_series = "PCR-.#####"
                    pcr.order_form = doc.name
                    pcr.item = row.items
                    pcr.item_description = frappe.db.get_value("Product", row.items, "item_description") or row.items
                    pcr.qty = row.qty or 0
                    pcr.customer_outlet = doc.name_of_outlet or doc.outlet or ""
                    pcr.dsp = doc.order_by or ""
                    pcr.original_price = base_price
                    pcr.new_price = row.price
                    pcr.requested_by = frappe.session.user
                    pcr.request_date = frappe.utils.now()
                    pcr.status = "Pending"
                    pcr.insert(ignore_permissions=True)
                    for role in ["Administrator", "President", "Manager"]:
                        users = frappe.get_all("Has Role",
                            filters={"role": role, "parenttype": "User"}, fields=["parent"])
                        for user in users:
                            if user.parent != frappe.session.user and frappe.db.get_value("User", user.parent, "enabled"):
                                frappe.get_doc({
                                    "doctype": "Notification Log",
                                    "for_user": user.parent,
                                    "from_user": frappe.session.user,
                                    "type": "Alert",
                                    "document_type": "Price Change Request",
                                    "document_name": pcr.name,
                                    "subject": "Price Change: " + (frappe.db.get_value("Product", row.items, "item_description") or row.items) + " on " + doc.name,
                                    "email_content": "Price changed from " + str(base_price) + " to " + str(row.price)
                                }).insert(ignore_permissions=True)


def on_update_after_submit(doc, method):
    # Merged from: Auto Create Sales on Approval, Approved/Rejected/Reserved/... Notification,
    # Auto Cancel Sales on Order Cancellation, Inventory Stock Out

    old_doc = doc.get_doc_before_save()
    old_wf = (old_doc.workflow_state or "") if old_doc else ""
    new_wf = doc.get("workflow_state") or ""

    # --- Auto Create Sales on Approval ---
    is_approved = new_wf == "Approved" and old_wf != "Approved"
    is_legacy_reserved = new_wf == "Reserved" and old_wf != "Reserved"
    if is_approved or is_legacy_reserved:
        existing = frappe.get_all("Sales", filters={"order_ref": doc.name}, limit=1)
        if existing:
            if not doc.get("sales_ref"):
                frappe.db.set_value("Order Form", doc.name, "sales_ref",
                                    existing[0].name, update_modified=False)
        else:
            source_rows = doc.get("table_mkaq") or doc.get("table_aaaa") or []
            items = [
                {
                    "doctype": "Sales Items Table",
                    "item": row.get("items"),
                    "qty": row.get("qty") or 0,
                    "unit": row.get("unit") or "",
                    "unit_price": row.get("price") or 0,
                    "total": row.get("total_price") or 0,
                    "warehouse": row.get("warehouse") or "",
                    "is_promo": row.get("is_promo_reward") or 0,
                }
                for row in source_rows if row.get("items")
            ]
            sales_total = doc.grand_total or 0
            sales = frappe.get_doc({
                "doctype": "Sales",
                "status": "Pending",
                "fulfillment_type": doc.get("fulfillment_type") or "Delivery",
                "order_ref": doc.name,
                "customer_link": doc.outlet or "",
                "customer_name": doc.name_of_outlet or doc.outlet or "",
                "address": doc.address or "",
                "contact_number": doc.contact_number or "",
                "grand_total": sales_total,
                "outstanding_balance": sales_total,
                "creation_date": frappe.utils.nowdate(),
                "items": items,
            })
            sales.insert(ignore_permissions=True)
            frappe.db.set_value("Order Form", doc.name, "sales_ref", sales.name, update_modified=False)

    # --- State Transition Notification ---
    state = new_wf
    if old_doc and old_doc.workflow_state == "Reserved" and state == "Approved":
        state = "Released"

    colors = {
        "Approved": "#0f62fe", "Rejected": "#da1e28", "Reserved": "#b28600",
        "Released": "#6f6f6f", "Dispatched": "#198038", "Delivered": "#005d5d",
        "Delivery Failed": "#a2191f", "Rescheduled": "#8a3ffc"
    }
    if state in colors:
        skip_duplicate_check = state in ["Dispatched", "Rescheduled", "Delivery Failed"]
        try:
            existing_logs = frappe.get_all("Notification Log", filters={
                "document_type": "Order Form",
                "document_name": doc.name,
                "subject": ["like", "%>" + state + "</%"]
            }, pluck="name") or []
        except Exception:
            existing_logs = []

        if skip_duplicate_check or not existing_logs:
            user = frappe.session.user or doc.get("modified_by") or doc.get("owner") or ""
            color = colors.get(state, "")
            styled_state = '<span style="color: ' + color + '; font-weight: bold;">' + state + "</span>"
            subject = doc.name + " was set as " + styled_state + " by " + user
            try:
                recipients = frappe.get_all("User", filters={"enabled": 1}, pluck="name") or []
            except Exception:
                recipients = []
            for u in recipients:
                try:
                    n = frappe.new_doc("Notification Log")
                    n.for_user = u
                    n.type = "Alert"
                    n.subject = subject
                    n.email_content = subject
                    n.document_type = "Order Form"
                    n.document_name = doc.name
                    n.insert(ignore_permissions=True)
                except Exception:
                    pass

    # --- Auto Cancel Sales on Order Cancellation ---
    if new_wf == "Canceled" and old_wf != "Canceled":
        sales_records = frappe.get_all("Sales",
            filters={"order_ref": doc.name, "status": ["!=", "Cancelled"]})
        if sales_records:
            frappe.db.set_value("Sales", sales_records[0].name, "status", "Cancelled")

    # --- Inventory Stock Out ---
    if doc.docstatus != 2:
        state_to_movement = {
            "Approved": "Reserved",
            "Reserved": "Reserved",
            "Dispatched": "Out",
            "Delivered": "Out",
            "Delivery Failed": "Return",
            "Redeliver": "Reserved",
            "Canceled": "Released",
            "Rejected": "Released"
        }
        movement_type = state_to_movement.get(new_wf)

        if movement_type:
            state_changed = old_doc and old_doc.workflow_state != new_wf

            if new_wf == "Reserved" and state_changed:
                for row in (doc.table_mkaq or []):
                    if not row.items or not row.warehouse:
                        continue
                    avail_data = frappe.db.sql("""
                        SELECT
                            COALESCE(SUM(CASE WHEN l.movement_type='In'       THEN t.qty ELSE 0 END), 0)
                            - COALESCE(SUM(CASE WHEN l.movement_type='Out'      THEN t.qty ELSE 0 END), 0)
                            - COALESCE(SUM(CASE WHEN l.movement_type='Reserved' THEN t.qty ELSE 0 END), 0)
                            + COALESCE(SUM(CASE WHEN l.movement_type='Released' THEN t.qty ELSE 0 END), 0)
                            + COALESCE(SUM(CASE WHEN l.movement_type='Return'   THEN t.qty ELSE 0 END), 0)
                            AS available
                        FROM `tabInventory Ledger` l
                        JOIN `tabInventory Ledger Table` t ON t.parent = l.name
                        WHERE t.product = %s AND l.warehouse = %s
                    """, (row.items, row.warehouse))
                    available = float(avail_data[0][0] if avail_data and avail_data[0][0] is not None else 0)
                    if float(row.qty or 0) > available:
                        frappe.throw(
                            "Insufficient stock for " + str(row.items) + " in " + str(row.warehouse) + ". "
                            "Available: " + str(int(available)) + ", Required: " + str(int(row.qty or 0)) + ". "
                            "Please adjust the order or restock before approving."
                        )

            user = frappe.session.user or doc.owner
            timestamp = frappe.utils.format_datetime(frappe.utils.now_datetime(), "yyyy-MM-dd HH:mm")
            timeline_entry = new_wf + "|" + (user or "") + "|" + (timestamp or "")

            wh_groups = {}
            for row in (doc.table_mkaq or []):
                wh = row.get("warehouse")
                if not row.items or not wh:
                    continue
                wh_groups.setdefault(wh, []).append(row)

            for wh, rows in wh_groups.items():
                existing = frappe.get_all("Inventory Ledger",
                    filters={"order_no": doc.name, "warehouse": wh},
                    order_by="creation asc", limit=1)

                if existing:
                    ledger = frappe.get_doc("Inventory Ledger", existing[0].name)
                    ledger.movement_type = movement_type
                    for r in ledger.table_jflv:
                        if movement_type == "Reserved":
                            r.qty_reserved = r.qty
                            r.qty_out = 0
                        elif movement_type == "Released":
                            r.qty_reserved = 0
                            r.qty_out = 0
                        elif movement_type == "Out":
                            r.qty_out = r.qty
                            r.qty_reserved = 0
                        elif movement_type == "Return":
                            r.qty_reserved = 0
                            r.qty_out = 0
                    if state_changed:
                        log = ledger.stock_movement_log or ""
                        log = (log + "\n" if log else "") + timeline_entry
                        ledger.db_set("stock_movement_log", log, update_modified=False)
                    ledger.save(ignore_permissions=True)
                else:
                    ledger = frappe.get_doc({
                        "doctype": "Inventory Ledger",
                        "movement_type": movement_type,
                        "order_no": doc.name,
                        "warehouse": wh,
                        "date_and_time": frappe.utils.now_datetime(),
                        "table_jflv": [],
                        "stock_movement_log": timeline_entry
                    })
                    for r in rows:
                        ledger.append("table_jflv", {
                            "product": r.items,
                            "unit": r.unit,
                            "qty": r.qty
                        })
                    ledger.insert(ignore_permissions=True)


def on_submit(doc, method):
    # Merged from: "Order Form Stock Notiffication" + "Order Submitted Notification"

    # --- Order Form Stock Notification ---
    items = doc.table_mkaq or []
    roles = ["President", "Manager", "Sales", "Purchaser", "Stock Manager", "Dispatcher"]
    role_users = frappe.get_all("Has Role", filters={"role": ["in", roles]}, fields=["parent"])
    user_list = list(set([u.parent for u in role_users] + ["Administrator"]))
    active_users = frappe.get_all("User",
        filters={"name": ["in", user_list], "enabled": 1}, pluck="name")

    for item in items:
        data = frappe.db.sql("""
            SELECT
                SUM(CASE WHEN l.movement_type = 'In' THEN t.qty ELSE 0 END)
                - SUM(CASE WHEN l.movement_type = 'Out' THEN t.qty ELSE 0 END)
                - SUM(CASE WHEN l.movement_type = 'Reserved' THEN t.qty ELSE 0 END)
                + SUM(CASE WHEN l.movement_type = 'Released' THEN t.qty ELSE 0 END)
                AS available_qty,
                p.reorder_level
            FROM `tabInventory Ledger` l
            JOIN `tabInventory Ledger Table` t ON t.parent = l.name
            LEFT JOIN `tabProduct` p ON p.name = t.product
            WHERE t.product = %s
            GROUP BY p.reorder_level
        """, item.product, as_dict=True)
        if not data:
            continue
        available = float(data[0].available_qty or 0)
        reorder = float(data[0].reorder_level or 0)
        if reorder == 0:
            continue
        if available <= 0:
            status = "STOCKOUT"
        elif available <= reorder * 0.2:
            status = "CRITICAL"
        elif available <= reorder:
            status = "WARNING"
        elif available <= reorder * 1.5:
            status = "MONITOR"
        else:
            continue
        for user in active_users:
            frappe.get_doc({
                "doctype": "Notification Log",
                "subject": f"{status} triggered by Order {doc.name}",
                "email_content": f"Order: {doc.name}\nProduct: {item.product}\nAvailable: {available}\nReorder Level: {reorder}\nNew Status: {status}",
                "for_user": user
            }).insert(ignore_permissions=True)

    # --- Order Submitted Notification ---
    user = frappe.session.user or doc.get("modified_by") or doc.get("owner") or ""
    styled_state = '<span style="color: #6929c4; font-weight: bold;">Submitted</span>'
    subject = doc.name + " was set as " + styled_state + " by " + user
    recipients = frappe.get_all("User", filters={"enabled": 1}, pluck="name") or []
    for u in recipients:
        n = frappe.new_doc("Notification Log")
        n.for_user = u
        n.type = "Alert"
        n.subject = subject
        n.email_content = subject
        n.document_type = "Order Form"
        n.document_name = doc.name
        n.insert(ignore_permissions=True)


def on_cancel(doc, method):
    # Merged from: "Order Canceled Notification" + "Inventory Stock Canceled"

    # --- Order Canceled Notification ---
    sys_subject_1 = "Order " + doc.name + " is now Canceled"
    sys_subject_2 = "Order " + doc.name + " is now Cancelled"
    logs = frappe.get_all("Notification Log", filters={
        "document_type": doc.doctype,
        "document_name": doc.name,
        "subject": ["in", [sys_subject_1, sys_subject_2]]
    }, pluck="name") or []
    for log_name in logs:
        frappe.delete_doc("Notification Log", log_name, ignore_permissions=True)

    user = frappe.session.user or doc.get("modified_by") or doc.get("owner") or ""
    styled_state = '<span style="color: #ff832b; font-weight: bold;">Cancelled</span>'
    subject = doc.name + " was set as " + styled_state + " by " + user
    recipients = frappe.get_all("User", filters={"enabled": 1}, pluck="name") or []
    for u in recipients:
        n = frappe.new_doc("Notification Log")
        n.for_user = u
        n.type = "Alert"
        n.subject = subject
        n.email_content = subject
        n.document_type = "Order Form"
        n.document_name = doc.name
        n.insert(ignore_permissions=True)

    # --- Inventory Stock Canceled ---
    existing = frappe.get_all("Inventory Ledger",
        filters={"order_no": doc.name},
        order_by="creation asc", limit=1)
    if existing:
        ledger = frappe.get_doc("Inventory Ledger", existing[0].name)
        if ledger.movement_type in ["Reserved", "Out"]:
            ledger.movement_type = "Return"
            for row in ledger.table_jflv:
                row.qty_reserved = 0
                row.qty_out = 0
            ledger.date_and_time = frappe.utils.now_datetime()
            ledger.remarks = f"stock returned due to cancellation of order {doc.name}"
            ledger.save(ignore_permissions=True)
