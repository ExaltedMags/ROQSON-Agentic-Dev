import roqson
import requests
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}

# Update Server Script: Auto Create Sales on Approval
script_content = """
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
        # Already has a Sales record — just ensure the link is set on Order Form
        if not doc.get('sales_ref'):
            frappe.db.set_value('Order Form', doc.name, 'sales_ref', existing[0].name,
                                update_modified=False)
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
            'status': 'Pending',  # Updated to Pending
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
        frappe.db.set_value('Order Form', doc.name, 'sales_ref', sales.name,
                            update_modified=False)
"""

roqson.update_doc('Server Script', 'Auto Create Sales on Approval', {'script': script_content})
print('Updated Auto Create Sales on Approval script')
