import roqson

wf_name = "Time in Time out"
doc = roqson.get_doc("Workflow", wf_name)

# 1. Check if Draft -> In Transit transition exists
transitions = doc.get("transitions", [])
has_dispatch = any(t.get("state") == "Draft" and t.get("next_state") == "In Transit" for t in transitions)

if not has_dispatch:
    print("Adding Draft -> In Transit transition (Action: Dispatch)...")
    
    # We'll add one for Dispatcher and one for Administrator
    # Roles: 'Dispatcher', 'Administrator', 'Driver'
    roles_to_add = ["Dispatcher", "Administrator", "Driver", "System Manager"]
    
    for role in roles_to_add:
        transitions.append({
            "state": "Draft",
            "action": "Dispatch",
            "next_state": "In Transit",
            "allowed": role,
            "allow_self_approval": 1,
            "doctype": "Workflow Transition"
        })
    
    # Update the doc
    roqson.update_doc("Workflow", wf_name, {"transitions": transitions})
    print("Workflow updated successfully.")
else:
    print("Transition already exists.")
