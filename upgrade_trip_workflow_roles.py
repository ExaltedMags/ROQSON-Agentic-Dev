import roqson

wf_name = "Time in Time out"
doc = roqson.get_doc("Workflow", wf_name)

transitions = doc.get("transitions", [])
roles_to_add = ["Dispatcher", "Administrator", "System Manager"]

# Add roles to existing actions if not already there
actions_to_upgrade = ["Time In", "Time Out"]

new_transitions = list(transitions)
for action in actions_to_upgrade:
    # Find existing next_state and state for this action
    existing = [t for t in transitions if t.get("action") == action]
    if existing:
        state = existing[0].get("state")
        next_state = existing[0].get("next_state")
        
        for role in roles_to_add:
            # Check if this role already has this transition
            if not any(t.get("state") == state and t.get("action") == action and t.get("allowed") == role for t in transitions):
                print(f"Adding {role} to action {action}...")
                new_transitions.append({
                    "state": state,
                    "action": action,
                    "next_state": next_state,
                    "allowed": role,
                    "allow_self_approval": 1,
                    "doctype": "Workflow Transition"
                })

if len(new_transitions) > len(transitions):
    roqson.update_doc("Workflow", wf_name, {"transitions": new_transitions})
    print("Workflow updated with additional roles.")
else:
    print("No updates needed for roles.")
