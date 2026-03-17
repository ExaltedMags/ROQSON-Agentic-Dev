import frappe
import json


# ---------------------------------------------------------------------------
# Customer Survey Form helpers
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_last_outlet_order(outlet=None):
    """CSF Get Last Order — last completed Sales for an outlet."""
    sale = frappe.get_all(
        "Sales",
        filters={"customer_link": outlet, "status": "Completed"},
        fields=["name", "creation_date"],
        order_by="creation_date desc",
        limit_page_length=1,
    )
    if not sale:
        return None

    doc = frappe.get_doc("Sales", sale[0].name)
    items = []
    for row in doc.items:
        product = frappe.db.get_value("Product", row.item, "item_description")
        items.append({"item_name": product or row.item, "qty": row.qty})

    return {"creation_date": doc.creation_date, "items": items}


@frappe.whitelist()
def get_survey_photos(doctype=None, docname=None):
    """CSF: Add Photos — return attached files for a given document."""
    files = frappe.get_all(
        "File",
        filters={"attached_to_doctype": doctype, "attached_to_name": docname},
        fields=["name", "file_url"],
        order_by="creation asc",
    )
    return files


# ---------------------------------------------------------------------------
# Inventory / Stock
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_product_stock(product=None, warehouse=None, mode=None):
    """Get Product Stock API — multi-mode stock query."""
    if mode == "get_all_products":
        res = frappe.db.sql(
            "SELECT DISTINCT t.product FROM `tabInventory Ledger Table` t",
            as_dict=True,
        )
        return [r.product for r in res]

    if mode == "analysis":
        total_products = frappe.db.count("Product")
        res_wh = frappe.db.sql(
            """
            SELECT l.warehouse, COUNT(DISTINCT t.product) as product_count
            FROM `tabInventory Ledger` l
            JOIN `tabInventory Ledger Table` t ON t.parent = l.name
            GROUP BY l.warehouse
            """,
            as_dict=True,
        )
        res_products = frappe.db.sql(
            "SELECT COUNT(DISTINCT t.product) as count FROM `tabInventory Ledger Table` t",
            as_dict=True,
        )
        return {
            "total_products": total_products,
            "products_with_any_inventory": res_products[0].count if res_products else 0,
            "warehouse_breakdown": res_wh,
        }

    if not product:
        return {"error": "No product provided"}

    wh_map = {"SJ": "WH-00001", "UG": "WH-00002"}
    query = """
        SELECT
            SUM(CASE WHEN l.movement_type = 'In' THEN t.qty ELSE 0 END) AS qty_in,
            SUM(CASE WHEN l.movement_type = 'Out' THEN t.qty ELSE 0 END) AS qty_out,
            SUM(CASE WHEN l.movement_type = 'Reserved' THEN t.qty ELSE 0 END) AS qty_reserved,
            SUM(CASE WHEN l.movement_type = 'Released' THEN t.qty ELSE 0 END) AS qty_released,
            SUM(CASE WHEN l.movement_type = 'Return' THEN t.qty ELSE 0 END) AS qty_return
        FROM `tabInventory Ledger` l
        JOIN `tabInventory Ledger Table` t ON t.parent = l.name
        WHERE t.product = %s
    """
    args = [product]
    if warehouse:
        target_wh = wh_map.get(warehouse, warehouse)
        query += " AND (l.warehouse = %s OR t.warehouse = %s)"
        args += [target_wh, target_wh]

    data = frappe.db.sql(query, tuple(args), as_dict=True)
    if data and data[0]:
        d = data[0]
        on_hand = (float(d.qty_in or 0) + float(d.qty_return or 0)) - float(d.qty_out or 0)
        reserved_net = float(d.qty_reserved or 0) - float(d.qty_released or 0)
        available = on_hand - reserved_net
        return {
            "on_hand": on_hand,
            "reserved": reserved_net,
            "available": available,
            "warehouse": warehouse or "All Warehouses",
        }
    return {"on_hand": 0, "reserved": 0, "available": 0, "warehouse": warehouse or "All Warehouses"}


@frappe.whitelist()
def get_promo_warehouse(product=None):
    """Get Promo Warehouse — return the warehouse with most available stock."""
    if not product:
        return {"error": "No product provided"}

    SJ_WH = "WH-00001"
    UG_WH = "WH-00002"

    def get_wh_stock(wh):
        data = frappe.db.sql(
            "SELECT"
            " SUM(CASE WHEN l.movement_type = 'In' THEN t.qty ELSE 0 END) -"
            " SUM(CASE WHEN l.movement_type = 'Out' THEN t.qty ELSE 0 END) -"
            " (SUM(CASE WHEN l.movement_type = 'Reserved' THEN t.qty ELSE 0 END) -"
            "  SUM(CASE WHEN l.movement_type = 'Released' THEN t.qty ELSE 0 END)) AS available"
            " FROM `tabInventory Ledger` l"
            " JOIN `tabInventory Ledger Table` t ON t.parent = l.name"
            " WHERE t.product = %s AND l.warehouse = %s",
            (product, wh),
            as_dict=True,
        )
        if data and data[0] and data[0].get("available") is not None:
            return float(data[0].get("available") or 0)
        return 0.0

    sj_stock = get_wh_stock(SJ_WH)
    ug_stock = get_wh_stock(UG_WH)

    if sj_stock <= 0 and ug_stock <= 0:
        return {"error": "No stock available in any warehouse", "sj_stock": sj_stock, "ug_stock": ug_stock}
    if ug_stock > sj_stock:
        return {"warehouse": UG_WH, "warehouse_name": "UG", "sj_stock": sj_stock, "ug_stock": ug_stock}
    return {"warehouse": SJ_WH, "warehouse_name": "SJ", "sj_stock": sj_stock, "ug_stock": ug_stock}


@frappe.whitelist()
def get_product_inventory(product=None):
    """Product: Get Inventory — per-warehouse inventory display."""
    data = frappe.db.sql(
        """
        SELECT
            w.name AS warehouse,
            COALESCE(i.in_qty,0)       AS in_qty,
            COALESCE(s.out_qty,0)      AS out_qty,
            COALESCE(r.reserved_qty,0) AS reserved_qty,
            (COALESCE(i.in_qty,0) - COALESCE(s.out_qty,0)) AS on_hand_qty,
            (COALESCE(i.in_qty,0) - COALESCE(s.out_qty,0) - COALESCE(r.reserved_qty,0)) AS available_qty
        FROM `tabWarehouses` w
        LEFT JOIN (
            SELECT t.product, l.warehouse, SUM(t.qty) AS in_qty
            FROM `tabInventory Entry` l
            JOIN `tabInventory Entry Table` t ON t.parent = l.name
            GROUP BY t.product, l.warehouse
        ) i ON i.warehouse = w.name AND i.product = %s
        LEFT JOIN (
            SELECT sitem.item AS product, sitem.warehouse, SUM(sitem.qty) AS out_qty
            FROM `tabSales` s
            JOIN `tabSales Items Table` sitem ON sitem.parent = s.name
            WHERE s.status IN ('Dispatching','In Transit','Received','Completed')
            GROUP BY sitem.item, sitem.warehouse
        ) s ON s.warehouse = w.name AND s.product = %s
        LEFT JOIN (
            SELECT r.items AS product, r.warehouse,
                SUM(CASE WHEN COALESCE(si.is_unreserved,0) = 1 THEN 0 ELSE r.qty END) AS reserved_qty
            FROM `tabOrder Form` o
            JOIN `tabOrder Details Table` r ON r.parent = o.name
            LEFT JOIN `tabSales` s ON s.order_ref = o.name
            LEFT JOIN `tabSales Items Table` si ON si.parent = s.name AND si.item = r.items
            WHERE o.workflow_state = 'Approved'
              AND (s.status IS NULL OR s.status NOT IN ('Dispatching','In Transit','Received','Completed'))
            GROUP BY r.items, r.warehouse
        ) r ON r.warehouse = w.name AND r.product = %s
        WHERE w.name IN ('WH-00001','WH-00002')
        """,
        (product, product, product),
        as_dict=True,
    )
    return data


# ---------------------------------------------------------------------------
# Trips / Orders helpers
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_eligible_orders(outlet=None, current_trip=None):
    """Eligible Orders by Outlet — Sales with status=Pending not yet on an active Trip."""
    outlet = outlet or ""
    current_trip = current_trip or ""

    if not outlet:
        return []

    if current_trip:
        active_sales = frappe.db.sql(
            """
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrips Table` ttt
            INNER JOIN `tabTrips` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
              AND tt.name != %(current_trip)s
            """,
            {"current_trip": current_trip},
            as_dict=True,
        )
    else:
        active_sales = frappe.db.sql(
            """
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrips Table` ttt
            INNER JOIN `tabTrips` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
            """,
            as_dict=True,
        )

    already_assigned = [r.sales_no for r in active_sales if r.sales_no]
    eligible = frappe.get_all(
        "Sales",
        filters={"status": "Pending", "customer_link": outlet},
        fields=["name", "customer_name", "grand_total", "order_ref", "sai_no"],
        limit_page_length=100,
    )
    return [s for s in eligible if s.name not in already_assigned]


@frappe.whitelist()
def stamp(trip_ticket=None, action=None, media_present=None):
    """Timestamping — server-side time injection for Trips time-in/out/proof/signature."""
    if not trip_ticket:
        frappe.throw("trip_ticket is required")
    if not action:
        frappe.throw("action is required")

    field_map = {
        "time_in": "arrival_time",
        "time_out": "completion_time",
        "proof": "proof_time_stamp",
        "signature": "signature_timestamp",
    }
    field = field_map.get(action)
    if not field:
        frappe.throw("Invalid action")

    doc = frappe.get_doc("Trips", trip_ticket)
    workflow_state = (doc.get("workflow_state") or "").strip()

    if action in ["time_in", "time_out"]:
        if workflow_state == "Draft":
            frappe.throw("Dispatch the Trips first before recording Time In or Time Out.")
        if workflow_state in ["Received", "Failed"]:
            frappe.throw("This Trips is already completed.")

    # Pad un-padded hours from frappe.utils.now() (e.g. "2:31:48" -> "02:31:48")
    now = frappe.utils.now()
    parts = now.split(" ", 1)
    if len(parts) == 2:
        date_part, time_part = parts
        time_segs = time_part.split(":")
        time_segs[0] = time_segs[0].zfill(2)
        if "." in time_segs[-1]:
            time_segs[-1] = time_segs[-1].split(".")[0]
        now = date_part + " " + ":".join(time_segs)

    media_present_bool = str(media_present).lower() in ("1", "true", "yes", "y")

    if action == "time_in":
        if doc.get("arrival_time"):
            frappe.throw("Time In already recorded.")
        value = now
        frappe.db.set_value("Trips", trip_ticket, field, value, update_modified=True)
    elif action == "time_out":
        if not doc.get("arrival_time"):
            frappe.throw("Time Out requires Time In first.")
        if doc.get("completion_time"):
            frappe.throw("Time Out already recorded.")
        value = now
        frappe.db.set_value("Trips", trip_ticket, field, value, update_modified=True)
    elif action in ("proof", "signature"):
        value = now if media_present_bool else None
        frappe.db.set_value("Trips", trip_ticket, field, value, update_modified=True)
    else:
        value = now
        frappe.db.set_value("Trips", trip_ticket, field, value, update_modified=True)

    new_modified = frappe.db.get_value("Trips", trip_ticket, "modified")
    return {"field": field, "value": value or "", "modified": str(new_modified)}


@frappe.whitelist()
def get_active_trip_order_names(current_trip=None):
    """Get Active Trip Order Names — prevents duplicate trip entries."""
    current_trip = current_trip or ""
    if current_trip:
        results = frappe.db.sql(
            """
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrips Table` ttt
            INNER JOIN `tabTrips` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
              AND tt.name != %(current_trip)s
            """,
            {"current_trip": current_trip},
            as_dict=True,
        )
    else:
        results = frappe.db.sql(
            """
            SELECT DISTINCT ttt.sales_no
            FROM `tabTrips Table` ttt
            INNER JOIN `tabTrips` tt ON tt.name = ttt.parent
            WHERE tt.docstatus != 2
              AND tt.delivery_status != 'Failed'
              AND ttt.sales_no IS NOT NULL
              AND ttt.sales_no != ''
            """,
            as_dict=True,
        )
    return [r.sales_no for r in results]


# ---------------------------------------------------------------------------
# Receipt / Sales helpers
# ---------------------------------------------------------------------------

@frappe.whitelist()
def get_receipt_history_for_sale(sales_no=None):
    """Return submitted Receipt Apply To rows for a given Sales record."""
    if not sales_no:
        return []

    rows = frappe.get_all(
        "Receipt Apply To",
        filters={"sales_no": sales_no, "docstatus": 1},
        fields=["name", "parent", "amount_applied", "outstanding_balance"],
        ignore_permissions=True,
        limit=200,
    )
    parent_names = list(set(r.parent for r in rows if r.parent))
    parents = {}
    if parent_names:
        receipts = frappe.get_all(
            "Receipt",
            filters=[["name", "in", parent_names]],
            fields=["name", "date", "payment_type", "user"],
            ignore_permissions=True,
            limit=200,
        )
        for p in receipts:
            parents[p.name] = p

    result = []
    for row in rows:
        p = parents.get(row.parent, {})
        result.append({
            "row_name": row.name,
            "receipt_no": row.parent,
            "date": p.get("date", ""),
            "payment_type": p.get("payment_type", ""),
            "amount_applied": row.amount_applied,
            "outstanding_balance": row.outstanding_balance,
            "user": p.get("user", ""),
        })
    return result


@frappe.whitelist()
def get_receivable_sales_for_customer(customer=None):
    """Return Received Sales for a customer — used by Receipt Apply To link filter."""
    filters = {"status": "Received"}
    if customer:
        filters["customer_link"] = customer

    return frappe.get_all(
        "Sales",
        filters=filters,
        fields=["name", "grand_total", "creation_date", "outstanding_balance"],
        order_by="creation_date desc",
        limit=200,
    )


@frappe.whitelist()
def get_customer_orders(customer=None, status=None, product=None, page=None, page_size=None):
    """Order History Summary — paginated order list for a customer."""
    page = int(page or 1)
    page_size = int(page_size or 20)
    limit_start = (page - 1) * page_size

    order_filters = {"outlet": customer}
    if status:
        order_filters["workflow_state"] = status

    if product:
        matching_orders = frappe.get_all(
            "Order Details Table",
            filters={"items": product},
            pluck="parent",
        )
        if not matching_orders:
            return {"orders": [], "has_more": False}
        order_filters["name"] = ["in", matching_orders]

    orders = frappe.get_all(
        "Order Form",
        filters=order_filters,
        fields=["name", "date", "grand_total", "workflow_state"],
        order_by="name desc",
        limit_start=limit_start,
        limit_page_length=page_size + 1,
        ignore_permissions=True,
    )

    has_more = len(orders) > page_size
    orders = orders[:page_size]

    if not orders:
        return {"orders": [], "has_more": False}

    order_names = [o["name"] for o in orders]
    items = frappe.get_all(
        "Order Details Table",
        filters={"parent": ["in", order_names]},
        fields=["parent", "items", "qty"],
    )
    product_ids = list({row["items"] for row in items if row.get("items")})
    products = frappe.get_all(
        "Product",
        filters={"name": ["in", product_ids]},
        fields=["name", "item_description"],
    )
    product_map = {p["name"]: p["item_description"] for p in products}
    item_map = {}
    qty_map = {}
    for row in items:
        label = product_map.get(row["items"], row["items"])
        item_map.setdefault(row["parent"], []).append(label + " (" + str(row["qty"]) + ")")
        qty_map[row["parent"]] = qty_map.get(row["parent"], 0) + (row.get("qty") or 0)

    for o in orders:
        o["items"] = ", ".join(item_map.get(o["name"], []))
        o["total_qty"] = qty_map.get(o["name"], 0)

    return {"orders": orders, "has_more": has_more}


# ---------------------------------------------------------------------------
# RPM — Role Permission Manager
# ---------------------------------------------------------------------------

@frappe.whitelist()
def rpm_get_doctype_fields(doctype=None):
    """RPM Get Fields — fields with permlevel grouping for a DocType."""
    if not doctype:
        frappe.throw("DocType is required")

    meta = frappe.get_meta(doctype)
    fields_by_level = {}
    for field in meta.fields:
        level = field.permlevel or 0
        fields_by_level.setdefault(level, []).append({
            "fieldname": field.fieldname,
            "label": field.label,
            "fieldtype": field.fieldtype,
            "reqd": field.reqd,
            "hidden": field.hidden,
        })

    return {
        "doctype_info": {
            "name": meta.name,
            "module": meta.module,
            "is_submittable": meta.is_submittable,
            "is_single": meta.issingle,
            "description": meta.description,
        },
        "fields_by_level": fields_by_level,
        "perm_levels": sorted(fields_by_level.keys()),
    }


@frappe.whitelist()
def rpm_get_field_permissions(doctype=None):
    """RPM Get Field Permissions — fields with current permlevel overrides."""
    if not doctype:
        frappe.throw("DocType is required")

    meta = frappe.get_meta(doctype)
    fields = []
    for field in meta.fields:
        if field.fieldtype not in ["Section Break", "Column Break", "Tab Break"]:
            fields.append({
                "fieldname": field.fieldname,
                "label": field.label or field.fieldname,
                "fieldtype": field.fieldtype,
                "permlevel": field.permlevel or 0,
                "reqd": field.reqd or 0,
                "hidden": field.hidden or 0,
                "read_only": field.read_only or 0,
            })

    custom_fields = frappe.get_all(
        "Property Setter",
        filters={"doc_type": doctype, "property": "permlevel"},
        fields=["field_name", "value"],
    )
    custom_permlevels = {cf.field_name: int(cf.value or 0) for cf in custom_fields}

    by_level = {}
    for field in fields:
        if field["fieldname"] in custom_permlevels:
            field["permlevel"] = custom_permlevels[field["fieldname"]]
            field["is_custom"] = True
        else:
            field["is_custom"] = False
        by_level.setdefault(field["permlevel"], []).append(field)

    return {
        "doctype": doctype,
        "fields": fields,
        "fields_by_level": by_level,
        "perm_levels": sorted(by_level.keys()),
    }


@frappe.whitelist()
def rpm_get_role_permissions(role=None):
    """RPM Get Permissions — all DocType permissions for a role."""
    if not role:
        frappe.throw("Role is required")

    perm_fields = [
        "parent", "permlevel", "read", "write", "create", "delete",
        "submit", "cancel", "amend", "report", "export", "share",
        "print", "email", "if_owner",
    ]
    standard_perms = frappe.get_all("DocPerm", filters={"role": role}, fields=perm_fields)
    custom_perms = frappe.get_all("Custom DocPerm", filters={"role": role}, fields=perm_fields)

    doctypes_with_custom = [
        d.parent for d in frappe.get_all("Custom DocPerm", fields=["parent"], distinct=True)
    ]

    permissions = []
    for perm in custom_perms:
        perm["doctype"] = perm["parent"]
        perm["is_custom"] = True
        permissions.append(perm)
    for perm in standard_perms:
        if perm["parent"] not in doctypes_with_custom:
            perm["doctype"] = perm["parent"]
            perm["is_custom"] = False
            permissions.append(perm)

    grouped = {}
    for perm in permissions:
        grouped.setdefault(perm["doctype"], []).append(perm)

    return {"role": role, "permissions": grouped, "total_doctypes": len(grouped)}


@frappe.whitelist()
def rpm_get_all_roles():
    """RPM Get Roles — all enabled roles with DocType permission counts."""
    roles = frappe.get_all(
        "Role",
        filters={"disabled": 0},
        fields=["name", "role_name", "desk_access", "is_custom"],
        order_by="role_name",
    )
    role_stats = []
    for role in roles:
        docperm_count = frappe.db.count("DocPerm", filters={"role": role.name})
        custom_docperm_count = frappe.db.count("Custom DocPerm", filters={"role": role.name})
        role_stats.append({
            "name": role.name,
            "role_name": role.role_name or role.name,
            "desk_access": role.desk_access,
            "is_custom": role.is_custom,
            "doctype_count": docperm_count + custom_docperm_count,
        })
    return role_stats


@frappe.whitelist()
def rpm_get_all_doctypes():
    """RPM Get Doctypes — all non-table DocTypes."""
    return frappe.get_all(
        "DocType",
        filters={"istable": 0},
        fields=["name", "module", "issingle", "is_submittable", "custom"],
        order_by="module, name",
    )


@frappe.whitelist()
def rpm_update_permission(role=None, doctype=None, permlevel=None, permissions=None):
    """RPM Update Permission — set role/DocType permission flags."""
    if not role or not doctype:
        frappe.throw("Role and DocType are required")

    permlevel = int(permlevel or 0)
    if isinstance(permissions, str):
        permissions = json.loads(permissions)

    valid_fields = [
        "read", "write", "create", "delete", "submit", "cancel",
        "amend", "report", "export", "share", "print", "email", "if_owner",
    ]

    existing = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": doctype, "role": role, "permlevel": permlevel},
        fields=["name"],
    )

    if existing:
        doc = frappe.get_doc("Custom DocPerm", existing[0].name)
        for key, value in permissions.items():
            if key in valid_fields:
                doc.set(key, value)
        doc.save()
        frappe.db.commit()
        return {"success": True}

    # Copy standard perms to custom if none exist yet
    if not frappe.get_all("Custom DocPerm", filters={"parent": doctype}):
        for std_perm in frappe.get_all("DocPerm", filters={"parent": doctype}, fields=["*"]):
            new_custom = frappe.new_doc("Custom DocPerm")
            new_custom.parent = doctype
            new_custom.parenttype = "DocType"
            new_custom.parentfield = "permissions"
            new_custom.role = std_perm.role
            new_custom.permlevel = std_perm.permlevel or 0
            for field in valid_fields:
                new_custom.set(field, std_perm.get(field) or 0)
            new_custom.insert()

    existing = frappe.get_all(
        "Custom DocPerm",
        filters={"parent": doctype, "role": role, "permlevel": permlevel},
        fields=["name"],
    )
    if existing:
        doc = frappe.get_doc("Custom DocPerm", existing[0].name)
        for key, value in permissions.items():
            if key in valid_fields:
                doc.set(key, value)
        doc.save()
    else:
        new_perm = frappe.new_doc("Custom DocPerm")
        new_perm.parent = doctype
        new_perm.parenttype = "DocType"
        new_perm.parentfield = "permissions"
        new_perm.role = role
        new_perm.permlevel = permlevel
        for key, value in permissions.items():
            if key in valid_fields:
                new_perm.set(key, value)
        new_perm.insert()

    frappe.db.commit()
    return {"success": True}


@frappe.whitelist()
def rpm_update_field_permlevel(doctype=None, fieldname=None, permlevel=None):
    """RPM Update Field Permlevel — set permlevel on a single field via Property Setter."""
    if not doctype or not fieldname:
        frappe.throw("DocType and fieldname are required")

    permlevel = int(permlevel or 0)
    existing = frappe.get_all(
        "Property Setter",
        filters={"doc_type": doctype, "field_name": fieldname, "property": "permlevel"},
        fields=["name"],
    )
    if existing:
        doc = frappe.get_doc("Property Setter", existing[0].name)
        doc.value = str(permlevel)
        doc.save()
    else:
        doc = frappe.new_doc("Property Setter")
        doc.doctype_or_field = "DocField"
        doc.doc_type = doctype
        doc.field_name = fieldname
        doc.property = "permlevel"
        doc.property_type = "Int"
        doc.value = str(permlevel)
        doc.insert()

    frappe.db.commit()
    frappe.clear_cache(doctype=doctype)
    return {"success": True, "message": "Field permission level updated"}


@frappe.whitelist()
def rpm_bulk_update_field_permlevels(doctype=None, updates=None):
    """RPM Bulk Update Fields — set permlevel on multiple fields at once."""
    if not doctype or not updates:
        frappe.throw("DocType and updates are required")

    if isinstance(updates, str):
        updates = json.loads(updates)

    for update in updates:
        fieldname = update.get("fieldname")
        permlevel = int(update.get("permlevel") or 0)
        existing = frappe.get_all(
            "Property Setter",
            filters={"doc_type": doctype, "field_name": fieldname, "property": "permlevel"},
            fields=["name"],
        )
        if existing:
            doc = frappe.get_doc("Property Setter", existing[0].name)
            doc.value = str(permlevel)
            doc.save()
        else:
            doc = frappe.new_doc("Property Setter")
            doc.doctype_or_field = "DocField"
            doc.doc_type = doctype
            doc.field_name = fieldname
            doc.property = "permlevel"
            doc.property_type = "Int"
            doc.value = str(permlevel)
            doc.insert()

    frappe.db.commit()
    frappe.clear_cache(doctype=doctype)
    return {"success": True, "message": "Field permission levels updated", "count": len(updates)}


# ---------------------------------------------------------------------------
# One-time utilities (keep disabled after migration)
# ---------------------------------------------------------------------------

@frappe.whitelist()
def fix_preferred_datetime_v2():
    """Fix Preferred Datetime Field v2 — strip time component from date-only field."""
    records = frappe.db.get_all(
        "Trips",
        filters=[["preferred_datetime", "!=", ""]],
        fields=["name", "preferred_datetime"],
    )
    for r in records:
        val = r.preferred_datetime
        if val and " " in val:
            frappe.db.set_value("Trips", r.name, "preferred_datetime", val.split(" ")[0])
    frappe.db.commit()
    return "Fixed " + str(len(records)) + " records"


@frappe.whitelist()
def fix_credit_application_table():
    """Fix Credit App — drop legacy schema columns from Credit Application."""
    columns = frappe.db.sql("DESCRIBE `tabCredit Application`", as_dict=True)
    frappe.msgprint("Current columns: " + str(len(columns)))
    try:
        frappe.db.sql("ALTER TABLE `tabCredit Application` DROP COLUMN `bank_reference_section`")
        frappe.msgprint("Dropped bank_reference_section column")
    except Exception as e:
        frappe.msgprint("Could not drop bank_reference_section: " + str(e))
    try:
        frappe.db.sql("ALTER TABLE `tabCredit Application` DROP COLUMN `table_vlik`")
        frappe.msgprint("Dropped table_vlik column")
    except Exception as e:
        frappe.msgprint("Could not drop table_vlik: " + str(e))
    frappe.db.commit()
    frappe.msgprint("Database changes committed. Now update the DocType in the UI.")


@frappe.whitelist()
def fix_order_titles_utility():
    """fix_order_titles_utility — backfill display_name for Orders missing it."""
    orders = frappe.db.get_list(
        "Order Form",
        filters={"display_name": ["like", "new-order-form%"]},
        fields=["name", "outlet"],
    )
    count = 0
    for o in orders:
        t = o.name + (" - " + o.outlet if o.outlet else "")
        frappe.db.set_value("Order Form", o.name, "display_name", t, update_modified=False)
        count += 1
    return count


@frappe.whitelist()
def temp_enable_order_form_comments():
    """temp_enable_order_form_comments — toggle hide_toolbar on Order Form DocType."""
    frappe.db.set_value("DocType", "Order Form", "hide_toolbar", 0)
    frappe.db.commit()
    val = frappe.db.get_value("DocType", "Order Form", "hide_toolbar")
    return {"hide_toolbar": val}


@frappe.whitelist()
def test_hello():
    """test_hello — connectivity test stub. Keep disabled."""
    return "hello"


@frappe.whitelist()
def trip_ticket_workflow_updater():
    """trip_ticket_workflow_updater — one-time workflow state setup. Keep disabled."""
    workflow = frappe.get_doc("Workflow", "Time in Time out")
    changed = False

    if not any(s.state == "Cancelled" for s in workflow.states):
        workflow.append("states", {
            "state": "Cancelled",
            "doc_status": "0",
            "allow_edit": "Administrator",
            "send_email": 0,
        })
        changed = True

    roles = ["Dispatcher", "Administrator", "System Manager", "Manager", "President"]
    states_to_cancel_from = ["Pending", "Draft", "In Transit"]
    for state in states_to_cancel_from:
        for role in roles:
            exists = any(
                t.state == state and t.action == "Cancel Trip" and t.allowed == role
                for t in workflow.transitions
            )
            if not exists:
                workflow.append("transitions", {
                    "state": state,
                    "action": "Cancel Trip",
                    "next_state": "Cancelled",
                    "allowed": role,
                    "allow_self_approval": 1,
                })
                changed = True

    if changed:
        workflow.save(ignore_permissions=True)
        return "Workflow updated"
    return "No changes needed"


@frappe.whitelist()
def trip_ticket_workflow_updater_v2():
    """Trip Ticket Workflow Updater (API) v2 — duplicate of v1. Keep disabled."""
    workflow = frappe.get_doc("Workflow", "Time in Time out")

    if not any(s.state == "Cancelled" for s in workflow.states):
        workflow.append("states", {
            "state": "Cancelled",
            "doc_status": "0",
            "allow_edit": "Administrator",
            "send_email": 0,
        })

    roles = ["Dispatcher", "Administrator", "System Manager", "Manager", "President"]
    states_to_cancel_from = ["Pending", "Draft", "In Transit"]
    for state in states_to_cancel_from:
        for role in roles:
            if not any(
                t.state == state and t.action == "Cancel Trip" and t.allowed == role
                for t in workflow.transitions
            ):
                workflow.append("transitions", {
                    "state": state,
                    "action": "Cancel Trip",
                    "next_state": "Cancelled",
                    "allowed": role,
                    "allow_self_approval": 1,
                })

    workflow.save(ignore_permissions=True)
    return "Workflow updated"
