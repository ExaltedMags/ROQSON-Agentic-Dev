import roqson
import json

doctypes_to_check = [
    "Order Form",
    "Sales",
    "Trip Ticket",
    "Customer Information",
    "Receipt"
]

try:
    all_doctypes = roqson.list_docs("DocType", fields=["name"], limit=5000)
    all_names = [d["name"] for d in all_doctypes]
except Exception as e:
    print(f"Failed to fetch doctypes: {e}")
    all_names = []

for dt in doctypes_to_check:
    actual_dt = dt
    if dt not in all_names:
        matches = [n for n in all_names if dt.lower() in n.lower()]
        if matches:
            actual_dt = matches[0]
            print(f"Warning: '{dt}' not found, using '{actual_dt}' instead.")
        else:
            print(f"Error: '{dt}' not found in DocTypes.")
            continue
            
    print(f"\n--- Schema for {actual_dt} ---")
    try:
        doc = roqson.get_doc("DocType", actual_dt)
        fields = doc.get("fields", [])
        field_names = [f.get("fieldname") for f in fields]
        
        status_fields = [f for f in fields if f.get("fieldname") in ["status", "workflow_state"]]
        for sf in status_fields:
            print(f"Field: {sf.get('fieldname')} ({sf.get('fieldtype')})")
            if sf.get('options'):
                print(f"Options:\n{sf.get('options')}")
            else:
                print("No options defined directly (might be driven by workflow).")
                
        workflows = roqson.list_docs("Workflow", fields=["name", "is_active", "document_type"], filters=[["document_type", "=", actual_dt], ["is_active", "=", 1]])
        states = []
        valid_workflow_states = set()
        if workflows:
            wf_name = workflows[0]["name"]
            wf_doc = roqson.get_doc("Workflow", wf_name)
            states = [s.get("state") for s in wf_doc.get("states", [])]
            valid_workflow_states.update(states)
            print(f"Active Workflow: {wf_name}")
            print(f"Workflow States: {states}")
        else:
            print("No active workflow found.")
            
        fields_to_fetch = ["name"]
        if "status" in field_names: fields_to_fetch.append("status")
        if "workflow_state" in field_names: fields_to_fetch.append("workflow_state")
        
        docs = roqson.list_docs(actual_dt, fields=fields_to_fetch, limit=5000)
        
        valid_statuses = set()
        for sf in status_fields:
            if sf.get('fieldname') == 'status' and sf.get('options'):
                valid_statuses.update([opt.strip() for opt in sf.get('options').split('\n') if opt.strip()])
                
        print(f"Total documents found: {len(docs)}")
        
        invalid_docs = []
        for d in docs:
            is_invalid = False
            reasons = []
            
            if 'status' in d and valid_statuses:
                if d['status'] not in valid_statuses:
                    is_invalid = True
                    reasons.append(f"Invalid status: '{d['status']}'")
            if 'workflow_state' in d and valid_workflow_states:
                if d['workflow_state'] not in valid_workflow_states:
                    is_invalid = True
                    reasons.append(f"Invalid workflow_state: '{d['workflow_state']}'")
                    
            if is_invalid:
                invalid_docs.append({"name": d["name"], "reasons": reasons, "doc": d})
                
        if invalid_docs:
            print(f"Found {len(invalid_docs)} documents with invalid statuses:")
            for ind in invalid_docs[:10]:
                print(f"  - {ind['name']}: {', '.join(ind['reasons'])}")
            if len(invalid_docs) > 10:
                print(f"  ... and {len(invalid_docs) - 10} more.")
        else:
            print("All checked documents have valid statuses/workflow states.")
            
    except Exception as e:
        print(f"Error checking {actual_dt}: {e}")
