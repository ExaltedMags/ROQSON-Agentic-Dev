import roqson

doc_name = 'Order-000309'
try:
    doc = roqson.get_doc("Order Form", doc_name)
    print(f"Name: {doc['name']}")
    print(f"Docstatus: {doc['docstatus']}")
    print(f"Workflow State: {doc.get('workflow_state')}")
    print(f"Status: {doc.get('status')}")
except Exception as e:
    print(f"Error: {e}")
