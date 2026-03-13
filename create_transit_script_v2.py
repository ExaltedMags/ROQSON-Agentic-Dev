import requests
import os

key = os.environ.get('ROQSON_API_KEY')
secret = os.environ.get('ROQSON_API_SECRET')
headers = {'Authorization': f'token {key}:{secret}'}

script_content = """
# Update Sales status to In Transit when Trip Ticket enters In Transit state
# DocType Event: Trip Ticket - Before Save

old = doc.get_doc_before_save()
old_wf = old.get('workflow_state') if old else ''
new_wf = doc.get('workflow_state')

if new_wf == 'In Transit' and old_wf != 'In Transit':
    if doc.table_cpme:
        for row in doc.table_cpme:
            if row.sales_no:
                # Only update if currently Dispatching
                current_status = frappe.db.get_value('Sales', row.sales_no, 'status')
                if current_status == 'Dispatching':
                    frappe.db.set_value('Sales', row.sales_no, 'status', 'In Transit')
"""

doc = {
    'doctype': 'Server Script',
    'name': 'Trip Ticket Transit Update',
    'script_type': 'DocType Event',
    'reference_doctype': 'Trip Ticket',
    'doctype_event': 'Before Save',
    'script': script_content,
    'disabled': 0
}

r = requests.post('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Server Script', json=doc, headers=headers)
print('Response:', r.status_code, r.text[:200])
