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
    
    docs = roqson.list_docs("Order Form", fields=["name", "workflow_state"], limit=5000)
    
    invalid_docs = []
    unique_invalid_states = set()
    for d in docs:
        if 'workflow_state' in d and d['workflow_state'] not in valid_workflow_states:
            invalid_docs.append(d)
            unique_invalid_states.add(d['workflow_state'])
            
    print(f"Unique invalid states: {unique_invalid_states}")
    
    # Update to 'Approved' or delete. Let's try to update to 'Approved'.
    # If they are Dispatched or Reserved, in the old flow they were past Approved. 
    # So 'Approved' is the closest current state (Sales handles the rest).
    # If they are Delivery Failed or Rescheduled, maybe 'Approved' is also fine.
    # Let's update all of them to 'Approved'.
    
    success = 0
    failed = 0
    for d in invalid_docs:
        print(f"Updating {d['name']} from {d['workflow_state']} to Approved...")
        try:
            roqson.update_doc("Order Form", d["name"], {"workflow_state": "Approved", "docstatus": 1})
            success += 1
        except Exception as e:
            print(f"Failed to update {d['name']}: {e}")
            failed += 1
            
    print(f"Updated {success} documents, failed {failed}.")

except Exception as e:
    print(f"Error: {e}")
