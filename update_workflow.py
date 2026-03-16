import roqson
import requests
import os

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": f"token {key}:{secret}"}

workflow = roqson.get_doc("Workflow", "Order Workflow")

# Add In Transit and Received to states if not present
existing_states = [s["state"] for s in workflow.get("states", [])]

new_states = []
if "In Transit" not in existing_states:
    new_states.append({
        "state": "In Transit",
        "doc_status": "1",
        "update_field": "workflow_state",
        "update_value": "In Transit",
        "allow_edit": "All",
        "doctype": "Workflow Document State"
    })

if "Received" not in existing_states:
    new_states.append({
        "state": "Received",
        "doc_status": "1",
        "update_field": "workflow_state",
        "update_value": "Received",
        "allow_edit": "All",
        "doctype": "Workflow Document State"
    })

if new_states:
    workflow["states"].extend(new_states)
    try:
        res = requests.put(f"https://roqson-industrial-sales.s.frappe.cloud/api/resource/Workflow/Order Workflow", json=workflow, headers=headers)
        print("Workflow update:", res.status_code)
    except Exception as e:
        print("Workflow update error:", e)
else:
    print("Workflow states already present.")
