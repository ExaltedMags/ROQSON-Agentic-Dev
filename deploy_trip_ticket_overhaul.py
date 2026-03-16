import json
import os
from copy import deepcopy

import requests
from dotenv import load_dotenv


load_dotenv(override=True)

BASE = "https://roqson-industrial-sales.s.frappe.cloud"


def headers():
    key = os.environ.get("ROQSON_API_KEY")
    secret = os.environ.get("ROQSON_API_SECRET")
    if not key or not secret:
        raise RuntimeError("Missing ROQSON_API_KEY or ROQSON_API_SECRET")
    return {
        "Authorization": "token " + key + ":" + secret,
        "Content-Type": "application/json",
    }


def request(method, path, **kwargs):
    response = requests.request(method, BASE + path, headers=headers(), timeout=60, **kwargs)
    if response.status_code >= 400:
        raise RuntimeError(str(response.status_code) + " " + response.text)
    if not response.text:
        return {}
    return response.json()


def get_doc(doctype, name):
    return request("GET", "/api/resource/" + doctype + "/" + requests.utils.quote(name, safe=""))["data"]


def list_docs(doctype, fields, filters=None, limit=200):
    params = {
        "fields": json.dumps(fields),
        "limit_page_length": limit,
        "order_by": "modified desc",
    }
    if filters:
        params["filters"] = json.dumps(filters)
    return request("GET", "/api/resource/" + doctype, params=params).get("data", [])


def insert_doc(doctype, data):
    payload = deepcopy(data)
    payload["doctype"] = doctype
    return request("POST", "/api/resource/" + doctype, json=payload)["data"]


def update_doc(doctype, name, data):
    return request(
        "PUT",
        "/api/resource/" + doctype + "/" + requests.utils.quote(name, safe=""),
        json=data,
    )["data"]


def ensure_custom_field(dt, fieldname, label, fieldtype, **extra):
    rows = list_docs(
        "Custom Field",
        ["name", "dt", "fieldname"],
        [["dt", "=", dt], ["fieldname", "=", fieldname]],
        1,
    )
    payload = {
        "dt": dt,
        "fieldname": fieldname,
        "label": label,
        "fieldtype": fieldtype,
    }
    payload.update(extra)
    if rows:
        print("Updating Custom Field:", dt, fieldname)
        return update_doc("Custom Field", rows[0]["name"], payload)
    print("Creating Custom Field:", dt, fieldname)
    return insert_doc("Custom Field", payload)


def sanitize_doctype_payload(doc):
    clean = {
        "name": doc["name"],
        "module": doc.get("module") or "Selling",
        "custom": 1,
        "istable": 1,
        "editable_grid": 1,
        "engine": doc.get("engine") or "InnoDB",
        "fields": [],
        "permissions": doc.get("permissions", []),
        "actions": [],
        "links": [],
    }
    for index, field in enumerate(doc.get("fields", [])):
        clean["fields"].append(
            {
                "fieldname": field["fieldname"],
                "label": field.get("label") or "",
                "fieldtype": field["fieldtype"],
                "options": field.get("options") or "",
                "reqd": field.get("reqd", 0),
                "hidden": field.get("hidden", 0),
                "read_only": field.get("read_only", 0),
                "in_list_view": field.get("in_list_view", 0),
                "default": field.get("default") or "",
                "idx": index + 1,
                "doctype": "DocField",
            }
        )
    return clean


def ensure_child_doctype(name, fields):
    try:
        doc = get_doc("DocType", name)
        current_map = {}
        for field in doc.get("fields", []):
            current_map[field.get("fieldname")] = field
        changed = False
        new_fields = []
        for field in fields:
            existing = current_map.get(field["fieldname"])
            merged = deepcopy(field)
            if existing:
                if (
                    existing.get("label") != merged.get("label")
                    or existing.get("fieldtype") != merged.get("fieldtype")
                    or (existing.get("options") or "") != (merged.get("options") or "")
                    or int(existing.get("reqd") or 0) != int(merged.get("reqd") or 0)
                    or int(existing.get("hidden") or 0) != int(merged.get("hidden") or 0)
                    or int(existing.get("read_only") or 0) != int(merged.get("read_only") or 0)
                    or int(existing.get("in_list_view") or 0) != int(merged.get("in_list_view") or 0)
                ):
                    changed = True
            else:
                changed = True
            new_fields.append(merged)
        if changed or len(new_fields) != len(doc.get("fields", [])):
            print("Updating child DocType:", name)
            update_doc("DocType", name, sanitize_doctype_payload({"name": name, "fields": new_fields, "permissions": doc.get("permissions", [])}))
        else:
            print("Child DocType already current:", name)
    except Exception:
        print("Creating child DocType:", name)
        insert_doc("DocType", sanitize_doctype_payload({"name": name, "fields": fields, "permissions": []}))


def ensure_client_script(name, dt, script, enabled=1):
    rows = list_docs("Client Script", ["name", "dt"], [["name", "=", name]], 1)
    payload = {"dt": dt, "enabled": enabled, "script": script}
    if rows:
        print("Updating Client Script:", name)
        return update_doc("Client Script", rows[0]["name"], payload)
    print("Creating Client Script:", name)
    payload["name"] = name
    return insert_doc("Client Script", payload)


def ensure_server_script(name, script_type, script, **extra):
    rows = list_docs("Server Script", ["name"], [["name", "=", name]], 1)
    payload = {"script_type": script_type, "script": script}
    payload.update(extra)
    if rows:
        print("Updating Server Script:", name)
        return update_doc("Server Script", rows[0]["name"], payload)
    print("Creating Server Script:", name)
    payload["name"] = name
    return insert_doc("Server Script", payload)


def patch_full_order_script():
    doc = get_doc("Client Script", "Full Order Script")
    script = doc.get("script") or ""
    script = script.replace('(frm.doc?.workflow_state || "") !== "Draft"', '!["Draft", "Pending"].includes((frm.doc?.workflow_state || "").trim())')
    script = script.replace('workflow_state == "Draft"', 'workflow_state == "Draft" || workflow_state == "Pending"')
    print("Patching Client Script: Full Order Script")
    update_doc("Client Script", "Full Order Script", {"script": script})


def ensure_workflow_state_doc(name, style=""):
    rows = list_docs("Workflow State", ["name"], [["name", "=", name]], 1)
    payload = {"workflow_state_name": name, "style": style}
    if rows:
        print("Workflow State already exists:", name)
        return
    print("Creating Workflow State:", name)
    payload["name"] = name
    insert_doc("Workflow State", payload)


def ensure_workflow():
    ensure_workflow_state_doc("Pending")
    ensure_workflow_state_doc("Completed", "Success")
    workflow = get_doc("Workflow", "Time in Time out")
    states = workflow.get("states", [])
    state_map = {}
    for state in states:
        state_map[state.get("state")] = state

    if "Pending" not in state_map:
        template = state_map.get("Draft") or (states[0] if states else {})
        states.append(
            {
                "state": "Pending",
                "doc_status": "0",
                "allow_edit": template.get("allow_edit") or "Administrator",
                "doctype": "Workflow Document State",
            }
        )
    if "Completed" not in state_map:
        template = state_map.get("Received") or (states[0] if states else {})
        states.append(
            {
                "state": "Completed",
                "doc_status": "0",
                "allow_edit": template.get("allow_edit") or "Administrator",
                "doctype": "Workflow Document State",
            }
        )

    ordered = []
    fresh_map = {}
    for state in states:
        fresh_map[state.get("state")] = state
    for name in ["Pending", "Draft", "In Transit", "Arrived", "Delivered", "Completed", "Received", "Failed"]:
        if name in fresh_map:
            ordered.append(fresh_map[name])
    for index, state in enumerate(ordered):
        state["idx"] = index + 1

    transitions = []
    seen = {}
    for tr in workflow.get("transitions", []):
        updated = deepcopy(tr)
        if updated.get("state") == "Draft":
            updated["state"] = "Pending"
        if updated.get("next_state") == "Received" and updated.get("action") == "Mark Delivered":
            updated["next_state"] = "Completed"
        key = updated.get("state") + "|" + updated.get("action") + "|" + updated.get("next_state") + "|" + updated.get("allowed")
        if key not in seen:
            seen[key] = 1
            transitions.append(updated)
    for index, tr in enumerate(transitions):
        tr["idx"] = index + 1

    print("Updating Workflow: Time in Time out")
    update_doc("Workflow", "Time in Time out", {"states": ordered, "transitions": transitions})


MULTI_DRIVER_SYNC_SCRIPT = """
# Trip Ticket multi-driver sync and validation
# DocType Event: Before Save
SALES_TABLE_FIELD = "table_cpme"
ITEM_TABLE_FIELD = "delivery_items"
DRIVER_TABLE_FIELD = "driver_assignments"
OUTLET_FIELD = "outlet"
CONTACT_FIELD = "contact_number"
ADDRESS_FIELD = "address"
CONTACT_PERSON_FIELD = "contact_person"
AREA_BARANGAY_FIELD = "area_barangay"
AREA_ZIP_FIELD = "area_zip_code"
SALES_DISPLAY_FIELD = "sales_numbers_display"
DRIVERS_DISPLAY_FIELD = "assigned_drivers_display"
TOTAL_QTY_FIELD = "total_item_qty"
TOTAL_LITERS_FIELD = "total_liters"
ALL_DONE_FIELD = "all_drivers_completed"
sales_rows = doc.get(SALES_TABLE_FIELD) or []
if not sales_rows:
    frappe.throw("Add at least one Sales row before saving the Trip Ticket.")
distinct_sales = []
sales_seen = {}
current_trip_sales = {}
if not doc.is_new():
    existing_rows = frappe.get_all("Trip Ticket Table", filters={"parent": doc.name}, fields=["sales_no"], limit_page_length=500)
    for existing_row in existing_rows:
        if existing_row.get("sales_no"):
            current_trip_sales[existing_row.get("sales_no")] = 1
for row in sales_rows:
    sales_no = row.get("sales_no")
    if not sales_no:
        frappe.throw("Every Sales row must have a Sales No.")
    if not sales_seen.get(sales_no):
        sales_seen[sales_no] = 1
        distinct_sales.append(sales_no)
first_sales = frappe.db.get_value("Sales", distinct_sales[0], ["status", "customer_link", "address", "contact_number", "order_ref"], as_dict=True) or {}
if not first_sales:
    frappe.throw("Sales record " + str(distinct_sales[0]) + " not found.")
if first_sales.get("status") != "Pending" and first_sales.get("status") != "Dispatching" and not current_trip_sales.get(distinct_sales[0]):
    frappe.throw("Sales record " + str(distinct_sales[0]) + " is not eligible (status must be Pending, got " + str(first_sales.get("status")) + ").")
first_outlet = first_sales.get("customer_link")
if not first_outlet:
    frappe.throw("Sales record " + str(distinct_sales[0]) + " has no customer.")
doc.set(OUTLET_FIELD, first_outlet)
doc.set(CONTACT_FIELD, first_sales.get("contact_number") or "")
doc.set(ADDRESS_FIELD, first_sales.get("address") or "")
if first_sales.get("order_ref"):
    contact_person = frappe.db.get_value("Order Form", first_sales.get("order_ref"), "contact_person") or ""
    if contact_person:
        doc.set(CONTACT_PERSON_FIELD, contact_person)
existing_items = {}
for row in doc.get(ITEM_TABLE_FIELD) or []:
    key = (row.get("sales_item_row") or "") + "::" + (row.get("sales_no") or "") + "::" + (row.get("item_code") or "")
    existing_items[key] = {"assigned_driver": row.get("assigned_driver") or "", "delivered": row.get("delivered") or 0}
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
        total_line_liters = float(item_qty or 0) * float(liters_per_unit or 0)
        key = str(item.get("name") or "") + "::" + str(sales_no) + "::" + str(item_code)
        previous = existing_items.get(key) or {}
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
        total_qty = total_qty + float(item_qty or 0)
        total_liters = total_liters + float(total_line_liters or 0)
customer = frappe.db.get_value("Customer Information", first_outlet, ["business_address", "residential_address"], as_dict=True) or {}
ph_address_name = customer.get("business_address") or customer.get("residential_address") or ""
ph_address = {}
if ph_address_name:
    ph_address = frappe.db.get_value("PH Address", ph_address_name, ["custom_barangay", "custom_zip_code"], as_dict=True) or {}
doc.set(AREA_BARANGAY_FIELD, ph_address.get("custom_barangay") or "")
doc.set(AREA_ZIP_FIELD, ph_address.get("custom_zip_code") or "")
doc.set(SALES_DISPLAY_FIELD, ", ".join(distinct_sales))
doc.set(TOTAL_QTY_FIELD, total_qty)
doc.set(TOTAL_LITERS_FIELD, total_liters)
assignment_rows = doc.get(DRIVER_TABLE_FIELD) or []
driver_counts = {}
driver_names = []
driver_map = {}
all_drivers_completed = 1
active_rows = 0
for drow in assignment_rows:
    if drow.get("driver"):
        active_rows = active_rows + 1
        driver_map[drow.get("driver")] = 1
for item_row in doc.get(ITEM_TABLE_FIELD) or []:
    assigned_driver = item_row.get("assigned_driver")
    if assigned_driver:
        if not driver_map.get(assigned_driver):
            frappe.throw("Assigned Driver " + str(assigned_driver) + " is missing from Driver Assignment.")
        driver_counts[assigned_driver] = (driver_counts.get(assigned_driver) or 0) + 1
for drow in assignment_rows:
    driver_name = drow.get("driver")
    if not driver_name:
        continue
    full_name = frappe.db.get_value("Driver", driver_name, "full_name") or driver_name
    driver_names.append(full_name)
    assigned_count = driver_counts.get(driver_name) or 0
    drow.assigned_items = str(assigned_count) + " item(s)"
    if drow.get("proof_of_delivery") and not drow.get("proof_time_stamp"):
        drow.proof_time_stamp = frappe.utils.now_datetime()
    if not drow.get("proof_of_delivery"):
        drow.proof_time_stamp = None
    if drow.get("submitted"):
        if assigned_count == 0:
            frappe.throw("Driver " + str(full_name) + " cannot submit without assigned items.")
        if not drow.get("proof_of_delivery"):
            frappe.throw("Driver " + str(full_name) + " must upload proof of delivery before submitting.")
        pending = 0
        for item_row in doc.get(ITEM_TABLE_FIELD) or []:
            if item_row.get("assigned_driver") == driver_name and not item_row.get("delivered"):
                pending = pending + 1
        if pending:
            frappe.throw("All assigned items must be checked off before marking delivery as complete.")
        if not drow.get("submitted_at"):
            drow.submitted_at = frappe.utils.now_datetime()
        if not drow.get("submitted_by"):
            drow.submitted_by = frappe.session.user
    else:
        all_drivers_completed = 0
        drow.submitted_at = None
        drow.submitted_by = ""
if active_rows == 0:
    all_drivers_completed = 0
doc.set(DRIVERS_DISPLAY_FIELD, ", ".join(driver_names))
doc.set(ALL_DONE_FIELD, all_drivers_completed)
legacy_final_state = (doc.get("workflow_state") or "") in ["Received", "Completed", "Failed"]
if doc.get("delivery_status") == "Successful" and not all_drivers_completed and (active_rows > 0 or not legacy_final_state):
    frappe.throw("All assigned items must be checked off before marking delivery as complete.")
if all_drivers_completed and active_rows > 0:
    doc.set("delivery_status", "Successful")
"""


TRACEABILITY_SCRIPT = """
# Trip Ticket traceability and Sales linking
# DocType Event: After Save
table_field = "table_cpme"
sales_names = {}
for row in doc.get(table_field) or []:
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
    for old_row in old.get(table_field) or []:
        old_sales = old_row.get("sales_no")
        if old_sales and not sales_names.get(old_sales):
            if frappe.db.get_value("Sales", old_sales, "trip_ticket") == doc.name:
                frappe.db.set_value("Sales", old_sales, "trip_ticket", "")
"""


DELIVERY_NOTIFICATION_SCRIPT = """
# Trip Ticket delivery completion notification
# DocType Event: Before Save
old = doc.get_doc_before_save()
old_completed = 0
if old:
    old_completed = old.get("all_drivers_completed") or 0
if (doc.get("workflow_state") or "").strip() == "Completed" and doc.get("delivery_status") == "Successful":
    for row in doc.get("table_cpme") or []:
        if row.get("sales_no"):
            frappe.db.set_value("Sales", row.get("sales_no"), "status", "Received")
if doc.get("all_drivers_completed") and not old_completed:
    recipients = {}
    sales_list = []
    driver_names = []
    for drow in doc.get("driver_assignments") or []:
        if drow.get("driver"):
            driver_names.append(frappe.db.get_value("Driver", drow.get("driver"), "full_name") or drow.get("driver"))
    customer = ""
    for row in doc.get("table_cpme") or []:
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
        message = message + " | " + customer
    if doc.get("address"):
        message = message + " | " + doc.get("address")
    if driver_names:
        message = message + " | Delivered by: " + ", ".join(driver_names)
    for user in recipients:
        if user and user != "Guest":
            frappe.get_doc({
                "doctype": "Notification Log",
                "for_user": user,
                "type": "Alert",
                "subject": "Delivery completed",
                "email_content": message,
                "document_type": "Trip Ticket",
                "document_name": doc.name
            }).insert(ignore_permissions=True)
"""


PERMISSION_QUERY_SCRIPT = """
conditions = "`tabTrip Ticket`.`archived` = 0"
driver_condition = ""
roles = frappe.get_all("Has Role", filters={"parent": frappe.session.user}, pluck="role")
if "Driver" in roles and "System Manager" not in roles and "Administrator" not in roles and "Dispatcher" not in roles:
    full_name = frappe.db.get_value("User", frappe.session.user, "full_name") or ""
    driver_names = frappe.get_all("Driver", filters={"full_name": full_name, "status": "Active"}, pluck="name")
    if driver_names:
        quoted = []
        for name in driver_names:
            quoted.append("'" + str(name).replace("'", "\\\\'") + "'")
        driver_condition = " and exists (select name from `tabTrip Ticket Driver Assignment` tt_da where tt_da.parent = `tabTrip Ticket`.name and tt_da.driver in (" + ", ".join(quoted) + ")) and `tabTrip Ticket`.`date` = CURDATE()"
    else:
        conditions = "1 = 0"
if conditions != "1 = 0":
    conditions = conditions + driver_condition
"""


LIST_VIEW_SCRIPT = """
frappe.listview_settings['Trip Ticket'] = {
  hide_name_column: true,
  hide_name_filter: true,
  add_fields: ['archived','trip_no','date','workflow_state','sales_numbers_display','assigned_drivers_display','total_item_qty','total_liters','area_barangay','area_zip_code','address'],
  formatters: {
    name(val, df, doc) {
      const text = doc.sales_numbers_display || doc.trip_no || val;
      return `<a href="/app/trip-ticket/${val}" class="level-item bold" style="font-weight:bold; font-size:14px;">${frappe.utils.escape_html(text)}</a>`;
    }
  },
  onload(listview) {
    if (listview.__tt_overhaul_loaded) return;
    listview.__tt_overhaul_loaded = true;
    if (!$(listview.page.wrapper).find('.tt-area-summary').length) {
      $(listview.page.wrapper).find('.layout-main-section').prepend('<div class="tt-area-summary" style="display:none; margin:12px 0 4px 0; padding:10px 14px; border-radius:10px; background:linear-gradient(135deg,#f4f0e8,#e7efe7); border:1px solid #d8dfd1;"></div>');
    }
    listview.page.add_menu_item('Show Active', () => apply_archive_view(listview, 'active'));
    listview.page.add_menu_item('Show Archived', () => apply_archive_view(listview, 'archived'));
    listview.page.add_menu_item('Show All', () => apply_archive_view(listview, 'all'));
    listview.page.add_inner_button('Today Only', () => apply_daily_filter(listview), 'Filter');
    listview.page.add_inner_button('Show All Dates', () => clear_daily_filter(listview), 'Filter');
  },
  refresh(listview) {
    setTimeout(() => {
      const header = listview.$result.find('.list-row-head .list-subject .list-subject-title');
      if (header.length) header.text('Sales No.');
      render_tt_rows(listview);
      render_tt_summary(listview);
    }, 120);
    if (!listview.__tt_default_archive_applied) {
      listview.__tt_default_archive_applied = true;
      const filters = listview.get_filters ? listview.get_filters() : [];
      const hasArchived = (filters || []).some(f => f[1] === 'archived');
      if (!hasArchived) {
        listview.filter_area.add([[listview.doctype, 'archived', '=', 0]]);
      }
    }
  }
};
function apply_archive_view(listview, mode) {
  listview.filter_area.clear(false).then(() => {
    if (mode === 'active') listview.filter_area.add([[listview.doctype, 'archived', '=', 0]]);
    if (mode === 'archived') listview.filter_area.add([[listview.doctype, 'archived', '=', 1]]);
    listview.refresh();
  });
}
function apply_daily_filter(listview) {
  const today = frappe.datetime.get_today();
  localStorage.removeItem('tt_daily_filter_disabled');
  listview.filter_area.clear(false).then(() => {
    listview.filter_area.add([[listview.doctype, 'date', '=', today]]);
    listview.filter_area.add([[listview.doctype, 'archived', '=', 0]]);
    listview.refresh();
  });
}
function clear_daily_filter(listview) {
  localStorage.setItem('tt_daily_filter_disabled', '1');
  listview.filter_area.clear(false).then(() => {
    listview.filter_area.add([[listview.doctype, 'archived', '=', 0]]);
    listview.refresh();
  });
}
function render_tt_rows(listview) {
  listview.$result.find('.list-row').each(function () {
    const name = $(this).attr('data-name');
    const doc = (listview.data || []).find(row => row.name === name);
    if (!doc) return;
    const parts = [];
    if (doc.assigned_drivers_display) parts.push('Drivers: ' + doc.assigned_drivers_display);
    if (doc.total_item_qty != null) parts.push('Qty: ' + doc.total_item_qty);
    if (doc.total_liters != null) parts.push('Liters: ' + doc.total_liters);
    if (doc.area_barangay || doc.area_zip_code) parts.push('Area: ' + [doc.area_barangay, doc.area_zip_code].filter(Boolean).join(' / '));
    if (doc.address) parts.push(doc.address);
    let holder = $(this).find('.tt-trip-meta');
    if (!holder.length) {
      holder = $('<div class="tt-trip-meta text-muted" style="font-size:12px; margin-top:4px; line-height:1.45;"></div>');
      $(this).find('.list-subject').append(holder);
    }
    holder.html(parts.map(line => '<div>' + frappe.utils.escape_html(String(line)) + '</div>').join(''));
  });
}
function render_tt_summary(listview) {
  const filters = listview.get_filters ? listview.get_filters() : [];
  const hasArea = (filters || []).some(f => f[1] === 'area_barangay' || f[1] === 'area_zip_code');
  const box = $(listview.page.wrapper).find('.tt-area-summary');
  if (!hasArea) {
    box.hide();
    return;
  }
  let qty = 0;
  let liters = 0;
  (listview.data || []).forEach(doc => {
    qty += Number(doc.total_item_qty || 0);
    liters += Number(doc.total_liters || 0);
  });
  box.html('<div style="font-size:11px; text-transform:uppercase; letter-spacing:.08em; color:#617061;">Area Volume Summary</div><div style="display:flex; gap:18px; margin-top:6px; font-size:14px;"><div><strong>Total Qty:</strong> ' + frappe.utils.escape_html(String(qty)) + '</div><div><strong>Total Liters:</strong> ' + frappe.utils.escape_html(String(liters.toFixed(2))) + '</div></div>');
  box.show();
}
"""


MULTI_DRIVER_CLIENT_SCRIPT = """
const TT_DRIVER_TABLE = 'driver_assignments';
const TT_ITEM_TABLE = 'delivery_items';
const TT_SALES_TABLE = 'table_cpme';
const TT_ITEM_ROW_DOCTYPE = 'Trip Ticket Delivery Item';

function tt_user_is_driver_only() {
  const roles = frappe.user_roles || [];
  return roles.includes('Driver') && !roles.includes('Administrator') && !roles.includes('System Manager') && !roles.includes('Dispatcher');
}

async function tt_resolve_current_driver_names(frm) {
  if (!tt_user_is_driver_only()) {
    frm.__tt_driver_names = [];
    return;
  }
  const rows = await frappe.db.get_list('Driver', {
    fields: ['name'],
    filters: { full_name: frappe.user.full_name(), status: 'Active' },
    limit: 20
  });
  frm.__tt_driver_names = (rows || []).map(row => row.name);
}

function tt_hide_deprecated_fields(frm) {
  ['driverhelper', 'proof_of_delivery', 'proof_time_stamp'].forEach(field => {
    if (frm.fields_dict[field]) frm.toggle_display(field, false);
  });
  if (tt_user_is_driver_only() && frm.fields_dict.information_section) {
    frm.toggle_display('information_section', false);
  }
}

function tt_has_selected_sales(frm) {
  return (frm.doc[TT_SALES_TABLE] || []).some(row => !!row.sales_no);
}

function tt_delivery_key(row) {
  return [row.sales_no || '', row.sales_item_row || '', row.item_code || ''].join('::');
}

async function tt_get_sales_doc(frm, salesNo) {
  frm.__tt_sales_doc_cache = frm.__tt_sales_doc_cache || {};
  if (!salesNo) return null;
  if (!frm.__tt_sales_doc_cache[salesNo]) {
    frm.__tt_sales_doc_cache[salesNo] = await frappe.db.get_doc('Sales', salesNo);
  }
  return frm.__tt_sales_doc_cache[salesNo];
}

async function tt_sync_delivery_items(frm) {
  const salesRows = frm.doc[TT_SALES_TABLE] || [];
  const existing = {};
  (frm.doc[TT_ITEM_TABLE] || []).forEach(row => {
    existing[tt_delivery_key(row)] = {
      name: row.name,
      assigned_driver: row.assigned_driver || '',
      delivered: row.delivered || 0,
      sales_no: row.sales_no || '',
      order_no: row.order_no || '',
      sales_item_row: row.sales_item_row || '',
      item_code: row.item_code || '',
      item_name: row.item_name || '',
      quantity: row.quantity || 0,
      liters_per_unit: row.liters_per_unit || 0,
      total_liters: row.total_liters || 0
    };
  });

  frm.clear_table(TT_ITEM_TABLE);

  for (const salesRow of salesRows) {
    const salesNo = salesRow.sales_no;
    if (!salesNo) continue;
    const salesDoc = await tt_get_sales_doc(frm, salesNo);
    const items = (salesDoc && salesDoc.items) || [];
    for (const item of items) {
      const itemCode = item.item || '';
      const salesItemRow = item.name || '';
      const key = [salesNo, salesItemRow, itemCode].join('::');
      const previous = existing[key] || {};
      const child = frm.add_child(TT_ITEM_TABLE, {
        sales_no: salesNo,
        order_no: salesDoc.order_ref || '',
        sales_item_row: salesItemRow,
        item_code: itemCode,
        item_name: previous.item_name || itemCode,
        quantity: item.qty || 0,
        liters_per_unit: previous.liters_per_unit || 0,
        total_liters: previous.total_liters || 0,
        assigned_driver: previous.assigned_driver || '',
        delivered: previous.delivered || 0
      });
      if (previous.name) {
        child.name = previous.name;
      }
    }
  }
  frm.refresh_field(TT_ITEM_TABLE);
}

function tt_toggle_delivery_table(frm) {
  const show = tt_has_selected_sales(frm);
  if (frm.fields_dict[TT_ITEM_TABLE]) {
    frm.toggle_display(TT_ITEM_TABLE, show);
  }
}

function tt_filter_delivery_rows(frm) {
  const grid = frm.fields_dict[TT_ITEM_TABLE] && frm.fields_dict[TT_ITEM_TABLE].grid;
  if (!grid) return;
  const driverNames = frm.__tt_driver_names || [];
  grid.grid_rows.forEach(row => {
    const assigned = row.doc.assigned_driver || '';
    const show = !tt_user_is_driver_only() || !assigned || driverNames.includes(assigned);
    $(row.row).toggle(show);
  });
}

function tt_find_driver_assignment_row(frm, driverName) {
  return (frm.doc[TT_DRIVER_TABLE] || []).find(row => row.driver === driverName);
}

function tt_ensure_driver_rows_from_items(frm) {
  const drivers = [];
  (frm.doc[TT_ITEM_TABLE] || []).forEach(row => {
    const driver = row.assigned_driver || '';
    if (driver && !drivers.includes(driver)) drivers.push(driver);
  });
  let changed = false;
  drivers.forEach(driver => {
    if (!tt_find_driver_assignment_row(frm, driver)) {
      frm.add_child(TT_DRIVER_TABLE, { driver: driver });
      changed = true;
    }
  });
  if (changed) frm.refresh_field(TT_DRIVER_TABLE);
}

function tt_recompute_driver_assignment_summary(frm) {
  tt_ensure_driver_rows_from_items(frm);
  const counts = {};
  (frm.doc[TT_ITEM_TABLE] || []).forEach(row => {
    const driver = row.assigned_driver || '';
    if (!driver) return;
    counts[driver] = (counts[driver] || 0) + 1;
  });
  (frm.doc[TT_DRIVER_TABLE] || []).forEach(row => {
    const count = counts[row.driver || ''] || 0;
    row.assigned_items = count ? (count + ' item(s)') : '';
  });
  frm.refresh_field(TT_DRIVER_TABLE);
}

function tt_apply_driver_query(frm) {
  frm.set_query('assigned_driver', TT_ITEM_TABLE, function () {
    return {
      filters: {
        status: 'Active'
      }
    };
  });
}

async function tt_sync_items_from_driver_table(frm, sourceDriver) {
  const itemRows = frm.doc[TT_ITEM_TABLE] || [];
  if (!itemRows.length || !sourceDriver) return;
  const driverRows = (frm.doc[TT_DRIVER_TABLE] || []).filter(row => !!row.driver);
  if (driverRows.length === 1) {
    for (const row of itemRows) {
      if (row.assigned_driver !== sourceDriver) {
        await frappe.model.set_value(TT_ITEM_ROW_DOCTYPE, row.name, 'assigned_driver', sourceDriver);
      }
    }
    return;
  }
  for (const row of itemRows) {
    if (!row.assigned_driver) {
      await frappe.model.set_value(TT_ITEM_ROW_DOCTYPE, row.name, 'assigned_driver', sourceDriver);
    }
  }
}

function tt_remove_custom_button_if_present(frm, label) {
  if (typeof frm.remove_custom_button === 'function') {
    frm.remove_custom_button(label);
    frm.remove_custom_button(label, 'Actions');
  }
}

async function tt_assign_all_items_to_driver(frm, driverName) {
  if (!driverName) return;
  if (!tt_find_driver_assignment_row(frm, driverName)) {
    frm.add_child(TT_DRIVER_TABLE, { driver: driverName });
    frm.refresh_field(TT_DRIVER_TABLE);
  }
  const rows = frm.doc[TT_ITEM_TABLE] || [];
  for (const row of rows) {
    if (!row.name) continue;
    await frappe.model.set_value(TT_ITEM_ROW_DOCTYPE, row.name, 'assigned_driver', driverName);
  }
  frm.refresh_field(TT_ITEM_TABLE);
  tt_recompute_driver_assignment_summary(frm);
  tt_filter_delivery_rows(frm);
}

function tt_add_bulk_assign_button(frm) {
  tt_remove_custom_button_if_present(frm, 'Assign All To Driver');
  if (!tt_has_selected_sales(frm)) return;
  if (tt_user_is_driver_only()) return;
  frm.add_custom_button('Assign All To Driver', () => {
    const dialog = new frappe.ui.Dialog({
      title: 'Assign All To Driver',
      fields: [
        {
          label: 'Driver',
          fieldname: 'driver',
          fieldtype: 'Link',
          options: 'Driver',
          get_query: () => ({ filters: { status: 'Active' } })
        }
      ],
      primary_action_label: 'Apply',
      primary_action: async (values) => {
        if (!values.driver) {
          frappe.msgprint('Select a driver first.');
          return;
        }
        await tt_assign_all_items_to_driver(frm, values.driver);
        dialog.hide();
      }
    });
    dialog.show();
  });
}

function tt_validate_rows_for_driver(frm, driverName) {
  const assigned = (frm.doc[TT_ITEM_TABLE] || []).filter(row => row.assigned_driver === driverName);
  if (!assigned.length) frappe.throw('No delivery items are assigned to this driver.');
  if (assigned.some(row => !row.delivered)) frappe.throw('All assigned items must be checked off before marking delivery as complete.');
}

function tt_add_submit_button(frm) {
  if (!tt_user_is_driver_only()) return;
  const driverNames = frm.__tt_driver_names || [];
  const target = (frm.doc[TT_DRIVER_TABLE] || []).find(row => driverNames.includes(row.driver) && !row.submitted);
  if (!target) return;
  frm.add_custom_button('Submit My Delivery', async () => {
    tt_validate_rows_for_driver(frm, target.driver);
    if (!target.proof_of_delivery) frappe.throw('Upload proof of delivery before submitting.');
    target.submitted = 1;
    target.submitted_by = frappe.session.user;
    frm.refresh_field(TT_DRIVER_TABLE);
    await frm.save();
  });
}

async function tt_refresh_delivery_ui(frm) {
  await tt_resolve_current_driver_names(frm);
  tt_hide_deprecated_fields(frm);
  await tt_sync_delivery_items(frm);
  tt_toggle_delivery_table(frm);
  tt_apply_driver_query(frm);
  tt_recompute_driver_assignment_summary(frm);
  tt_filter_delivery_rows(frm);
  tt_add_submit_button(frm);
  tt_add_bulk_assign_button(frm);
}

frappe.ui.form.on('Trip Ticket', {
  async refresh(frm) {
    await tt_refresh_delivery_ui(frm);
  }
});

frappe.ui.form.on('Trip Ticket Table', {
  async sales_no(frm) {
    await tt_sync_delivery_items(frm);
    tt_toggle_delivery_table(frm);
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
  },
  async form_render(frm, cdt, cdn) {
    await tt_sync_delivery_items(frm);
    tt_toggle_delivery_table(frm);
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
  }
});

frappe.ui.form.on('Trip Ticket Driver Assignment', {
  async driver(frm, cdt, cdn) {
    const row = locals[cdt] && locals[cdt][cdn];
    tt_apply_driver_query(frm);
    if (row && row.driver) {
      await tt_sync_items_from_driver_table(frm, row.driver);
    }
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
    tt_add_bulk_assign_button(frm);
  },
  async vehicle(frm) {
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
  }
});

frappe.ui.form.on('Trip Ticket Delivery Item', {
  async assigned_driver(frm) {
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
    tt_add_bulk_assign_button(frm);
  },
  delivered(frm) {
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
  },
  form_render(frm) {
    tt_recompute_driver_assignment_summary(frm);
    tt_filter_delivery_rows(frm);
  }
});
"""


def deploy_schema():
    ensure_child_doctype(
        "Trip Ticket Driver Assignment",
        [
            {"fieldname": "driver", "label": "Driver", "fieldtype": "Link", "options": "Driver", "reqd": 1, "in_list_view": 1},
            {"fieldname": "vehicle", "label": "Vehicle", "fieldtype": "Link", "options": "Vehicles", "in_list_view": 1},
            {"fieldname": "assigned_items", "label": "Assigned Items", "fieldtype": "Data", "read_only": 1, "in_list_view": 1},
            {"fieldname": "proof_of_delivery", "label": "Proof of Delivery", "fieldtype": "Attach"},
            {"fieldname": "proof_time_stamp", "label": "POD Time", "fieldtype": "Datetime", "read_only": 1},
            {"fieldname": "submitted", "label": "Submitted", "fieldtype": "Check"},
            {"fieldname": "submitted_at", "label": "Submitted At", "fieldtype": "Datetime", "read_only": 1},
            {"fieldname": "submitted_by", "label": "Submitted By", "fieldtype": "Data", "read_only": 1},
        ],
    )
    ensure_child_doctype(
        "Trip Ticket Delivery Item",
        [
            {"fieldname": "sales_no", "label": "Sales No.", "fieldtype": "Link", "options": "Sales", "read_only": 1, "in_list_view": 1},
            {"fieldname": "order_no", "label": "Order No.", "fieldtype": "Link", "options": "Order Form", "read_only": 1},
            {"fieldname": "sales_item_row", "label": "Sales Item Row", "fieldtype": "Data", "hidden": 1},
            {"fieldname": "item_code", "label": "Item", "fieldtype": "Link", "options": "Product", "read_only": 1, "in_list_view": 1},
            {"fieldname": "item_name", "label": "Item Name", "fieldtype": "Data", "read_only": 1},
            {"fieldname": "quantity", "label": "Quantity", "fieldtype": "Float", "read_only": 1, "in_list_view": 1},
            {"fieldname": "liters_per_unit", "label": "Liters / Unit", "fieldtype": "Float", "read_only": 1},
            {"fieldname": "total_liters", "label": "Total Liters", "fieldtype": "Float", "read_only": 1},
            {"fieldname": "assigned_driver", "label": "Assigned Driver", "fieldtype": "Link", "options": "Driver", "in_list_view": 1},
            {"fieldname": "delivered", "label": "Delivered", "fieldtype": "Check", "in_list_view": 1},
        ],
    )
    ensure_custom_field("Trip Ticket", "delivery_items", "Item Assignment", "Table", options="Trip Ticket Delivery Item", insert_after="table_cpme")
    ensure_custom_field("Trip Ticket", "driver_assignments", "Driver Assignment", "Table", options="Trip Ticket Driver Assignment", insert_after="delivery_items")
    ensure_custom_field("Trip Ticket", "sales_numbers_display", "Sales No.", "Small Text", read_only=1, in_list_view=1, in_standard_filter=1, insert_after="trip_no")
    ensure_custom_field("Trip Ticket", "assigned_drivers_display", "Assigned Drivers", "Small Text", read_only=1, in_list_view=1, insert_after="sales_numbers_display")
    ensure_custom_field("Trip Ticket", "total_item_qty", "No. of Items", "Float", read_only=1, in_list_view=1, in_standard_filter=1, insert_after="assigned_drivers_display")
    ensure_custom_field("Trip Ticket", "total_liters", "Liters", "Float", read_only=1, in_list_view=1, in_standard_filter=1, insert_after="total_item_qty")
    ensure_custom_field("Trip Ticket", "area_barangay", "Area Barangay", "Link", options="PH Barangay", read_only=1, in_standard_filter=1, insert_after="total_liters")
    ensure_custom_field("Trip Ticket", "area_zip_code", "Area ZIP Code", "Data", read_only=1, in_standard_filter=1, insert_after="area_barangay")
    ensure_custom_field("Trip Ticket", "all_drivers_completed", "All Drivers Completed", "Check", read_only=1, insert_after="area_zip_code")
    ensure_custom_field("Sales", "trip_ticket", "Trip Ticket", "Link", options="Trip Ticket", insert_after="order_ref")
    ensure_custom_field("Vehicles", "custom_capacity_liters", "Capacity (Liters)", "Float", insert_after="model")
    ensure_custom_field("Vehicles", "custom_road_constraint", "Road Constraint", "Select", options="\nSmall Trucks Only\nStandard Access\nLarge Vehicle Access", insert_after="custom_capacity_liters")
    ensure_custom_field("Product", "custom_liters", "Liters", "Float", insert_after="product_name")


def deploy_scripts():
    ensure_server_script("Trip Ticket Multi-Driver Sync", "DocType Event", MULTI_DRIVER_SYNC_SCRIPT, reference_doctype="Trip Ticket", event_frequency="All", doctype_event="Before Save", disabled=0)
    ensure_server_script("Trip Ticket and Order Form Traceability", "DocType Event", TRACEABILITY_SCRIPT, reference_doctype="Trip Ticket", event_frequency="All", doctype_event="After Save", disabled=0)
    ensure_server_script("Delivery Status Notification", "DocType Event", DELIVERY_NOTIFICATION_SCRIPT, reference_doctype="Trip Ticket", event_frequency="All", doctype_event="Before Save", disabled=0)
    ensure_server_script("Archive Trip Ticket", "Permission Query", PERMISSION_QUERY_SCRIPT, reference_doctype="Trip Ticket", disabled=0)
    ensure_client_script("Archive Trip Ticket List", "Trip Ticket", LIST_VIEW_SCRIPT, 1)
    ensure_client_script("Trip Ticket: Multi-Driver Operations", "Trip Ticket", MULTI_DRIVER_CLIENT_SCRIPT, 1)
    patch_full_order_script()


def verify():
    rows = list_docs("Custom Field", ["fieldname"], [["dt", "=", "Trip Ticket"]], 100)
    fieldnames = []
    for row in rows:
        fieldnames.append(row.get("fieldname"))
    for expected in ["driver_assignments", "delivery_items", "sales_numbers_display", "assigned_drivers_display", "total_item_qty", "total_liters", "area_barangay", "area_zip_code", "all_drivers_completed"]:
        if expected not in fieldnames:
            raise RuntimeError("Missing Trip Ticket field " + expected)
    print("Verification passed.")


if __name__ == "__main__":
    deploy_schema()
    ensure_workflow()
    deploy_scripts()
    verify()
