import roqson

try:
    doc = roqson.get_doc("DocType", "Order Form")
    fields = doc.get("fields", [])
    
    workflows = roqson.list_docs("Workflow", fields=["name", "is_active", "document_type"], filters=[["document_type", "=", "Order Form"], ["is_active", "=", 1]])
    states = []
    if workflows:
        wf_name = workflows[0]["name"]
        wf_doc = roqson.get_doc("Workflow", wf_name)
        states = [s.get("state") for s in wf_doc.get("states", [])]
        
    valid_workflow_states = set(states)
    
    docs = roqson.list_docs("Order Form", fields=["name", "workflow_state", "docstatus"], limit=5000)
    
    invalid_docs = []
    for d in docs:
        if 'workflow_state' in d and d['workflow_state'] not in valid_workflow_states:
            invalid_docs.append(d)
            
    print(f"Found {len(invalid_docs)} invalid docs.")
    
    success = 0
    failed = 0
    for d in invalid_docs:
        print(f"Cancelling {d['name']} from {d['workflow_state']}...")
        try:
            # First try client.cancel
            res = roqson.call_method("frappe.client.cancel", doctype="Order Form", name=d["name"])
            print(f"Cancelled {d['name']}")
            success += 1
        except Exception as e:
            print(f"Failed to cancel {d['name']} via frappe.client.cancel: {e}")
            try:
                # Try setting docstatus to 2 directly if it fails
                roqson.update_doc("Order Form", d["name"], {"docstatus": 2})
                print(f"Cancelled {d['name']} via update_doc")
                success += 1
            except Exception as e2:
                print(f"Failed to cancel {d['name']} via update_doc: {e2}")
                failed += 1
            
    print(f"Successfully cancelled {success} documents, failed {failed}.")

except Exception as e:
    print(f"Error: {e}")
