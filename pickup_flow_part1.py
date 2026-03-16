import roqson
import requests
import os
import json

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": f"token {key}:{secret}"}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

# 1. Add fulfillment_type to Order Form
print("Fetching Order Form...")
order_doctype = roqson.get_doc("DocType", "Order Form")
fields = order_doctype.get("fields", [])
has_ft_order = any(f.get("fieldname") == "fulfillment_type" for f in fields)

if not has_ft_order:
    print("Adding fulfillment_type to Order Form")
    # Insert before order_by or date
    idx_insert = next((i for i, f in enumerate(fields) if f.get("fieldname") == "date"), 0)
    new_field = {
        "fieldname": "fulfillment_type",
        "label": "Fulfillment Type",
        "fieldtype": "Select",
        "options": "Delivery\nPick-up",
        "default": "Delivery",
        "reqd": 1,
        "in_list_view": 1,
        "doctype": "DocField"
    }
    fields.insert(idx_insert, new_field)
    for i, f in enumerate(fields):
        f["idx"] = i + 1
    
    res = requests.put(f"{BASE_URL}/api/resource/DocType/Order Form", json=order_doctype, headers=headers)
    print("Order Form Field Add:", res.status_code)

# 2. Add fulfillment_type to Sales
print("Fetching Sales...")
sales_doctype = roqson.get_doc("DocType", "Sales")
fields_sales = sales_doctype.get("fields", [])
has_ft_sales = any(f.get("fieldname") == "fulfillment_type" for f in fields_sales)

if not has_ft_sales:
    print("Adding fulfillment_type to Sales")
    idx_insert = next((i for i, f in enumerate(fields_sales) if f.get("fieldname") == "status"), 0)
    new_field = {
        "fieldname": "fulfillment_type",
        "label": "Fulfillment Type",
        "fieldtype": "Select",
        "options": "Delivery\nPick-up",
        "default": "Delivery",
        "read_only": 1,
        "in_list_view": 1,
        "doctype": "DocField"
    }
    fields_sales.insert(idx_insert + 1, new_field)
    for i, f in enumerate(fields_sales):
        f["idx"] = i + 1
        
    res = requests.put(f"{BASE_URL}/api/resource/DocType/Sales", json=sales_doctype, headers=headers)
    print("Sales Field Add:", res.status_code)

# 3. Update Auto Create Sales Server Script
auto_create_script = """
# Auto Create Sales on Order Approval
# DocType Event: Order Form — After Save (Submitted Document)

old_doc = doc.get_doc_before_save()
if not old_doc:
    old_wf = ""
else:
    old_wf = old_doc.workflow_state or ""

# Trigger on transition TO Approved (or Reserved if that legacy state still hits)
is_approved = doc.workflow_state == 'Approved' and old_wf != 'Approved'
is_legacy_reserved = doc.workflow_state == 'Reserved' and old_wf != 'Reserved'

if not (is_approved or is_legacy_reserved):
    pass
else:
    # Check if a Sales record already exists for this order
    existing = frappe.get_all('Sales', filters={'order_ref': doc.name}, limit=1)
    if existing:
        if not doc.get('sales_ref'):
            frappe.db.set_value('Order Form', doc.name, 'sales_ref', existing[0].name, update_modified=False)
    else:
        # Mirror items from Order Details Table
        items = []
        for row in (doc.table_mkaq or []):
            if row.items:
                items.append({
                    'doctype': 'Sales Items Table',
                    'item': row.items,
                    'qty': row.qty or 0,
                    'unit': row.unit or "",
                    'unit_price': row.price or 0,
                    'total': row.total_price or 0,
                    'warehouse': row.warehouse or "",
                    'is_promo': row.is_promo_reward or 0,
                })

        sales = frappe.get_doc({
            'doctype': 'Sales',
            'status': 'Pending',
            'fulfillment_type': doc.get('fulfillment_type') or 'Delivery',
            'order_ref': doc.name,
            'customer_link': doc.outlet or "",
            'customer_name': doc.name_of_outlet or doc.outlet or "",
            'address': doc.address or "",
            'contact_number': doc.contact_number or "",
            'grand_total': doc.grand_total or 0,
            'creation_date': frappe.utils.nowdate(),
            'items': items,
        })
        sales.insert(ignore_permissions=True)

        # Link back to Order Form
        frappe.db.set_value('Order Form', doc.name, 'sales_ref', sales.name, update_modified=False)
"""
roqson.update_doc("Server Script", "Auto Create Sales on Approval", {"script": auto_create_script})
print("Updated Auto Create Sales on Approval")

# 4. Create Sales Pick-up Confirmation Client Script
pickup_client_script = """
frappe.ui.form.on('Sales', {
    refresh(frm) {
        // Pick-up button logic for Warehouse and Admin
        const roles = frappe.user_roles;
        const can_confirm = roles.includes('Administrator') || roles.includes('System Manager') || roles.includes('Warehouse');
        
        if (frm.doc.fulfillment_type === 'Pick-up' && frm.doc.status === 'Pending' && can_confirm) {
            frm.page.add_inner_button('Confirm Pick-up', () => {
                frappe.confirm('Has the customer collected these items from the warehouse?', () => {
                    frm.set_value('status', 'Received');
                    frm.save();
                });
            }).addClass('btn-primary').css({'color': 'white', 'background-color': '#166534', 'border-color': '#166534'});
        }
    }
});
"""

doc_pickup_client = {
    'doctype': 'Client Script',
    'name': 'Sales Pick-up Confirmation',
    'dt': 'Sales',
    'script': pickup_client_script,
    'enabled': 1
}

try:
    roqson.update_doc("Client Script", "Sales Pick-up Confirmation", doc_pickup_client)
    print("Updated Sales Pick-up Confirmation")
except Exception:
    requests.post(f"{BASE_URL}/api/resource/Client Script", json=doc_pickup_client, headers=headers)
    print("Created Sales Pick-up Confirmation")

# 5. Create Sales Inventory Stock Out Server Script
sales_stock_script = """
# Handle Inventory Stock Out for Sales status transitions (Received/Failed)
# DocType Event: Sales - After Save

old_doc = doc.get_doc_before_save()
if old_doc:
    old_status = old_doc.status
    new_status = doc.status

    if new_status != old_status:
        movement_type = None
        if new_status == "Received":
            movement_type = "Out"
        elif new_status == "Failed":
            movement_type = "Return"

        if movement_type and doc.order_ref:
            # Find associated Inventory Ledger
            ledgers = frappe.get_all("Inventory Ledger", filters={"order_no": doc.order_ref})
            for l in ledgers:
                ledger = frappe.get_doc("Inventory Ledger", l.name)
                ledger.movement_type = movement_type

                for r in ledger.table_jflv:
                    if movement_type == "Out":
                        r.qty_out = r.qty
                        r.qty_reserved = 0
                    elif movement_type == "Return":
                        r.qty_reserved = 0
                        r.qty_out = 0

                user = frappe.session.user or doc.owner
                timestamp = frappe.utils.format_datetime(frappe.utils.now_datetime(), "yyyy-MM-dd HH:mm")
                timeline_entry = new_status + "|" + (user or "") + "|" + (timestamp or "")

                log = ledger.stock_movement_log or ""
                log = (log + "\\n" if log else "") + timeline_entry
                ledger.db_set("stock_movement_log", log, update_modified=False)

                ledger.save(ignore_permissions=True)
"""

doc_sales_stock = {
    'doctype': 'Server Script',
    'name': 'Sales Inventory Stock Out',
    'script_type': 'DocType Event',
    'reference_doctype': 'Sales',
    'doctype_event': 'After Save',
    'script': sales_stock_script,
    'disabled': 0
}

try:
    roqson.update_doc("Server Script", "Sales Inventory Stock Out", doc_sales_stock)
    print("Updated Sales Inventory Stock Out")
except Exception:
    requests.post(f"{BASE_URL}/api/resource/Server Script", json=doc_sales_stock, headers=headers)
    print("Created Sales Inventory Stock Out")

print("Done updating schemas and backend scripts")
