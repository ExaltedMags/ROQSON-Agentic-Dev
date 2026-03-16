import roqson
import requests
import os
import json

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": f"token {key}:{secret}"}
BASE_URL = "https://roqson-industrial-sales.s.frappe.cloud"

def update_order_form():
    # 1. Update DocType options
    order_doc = roqson.get_doc("DocType", "Order Form")
    target_options = ["Draft", "Needs Review", "Approved", "Canceled"]
    
    for f in order_doc.get("fields", []):
        if f.get("fieldname") == "workflow_state":
            f["options"] = "\n".join(target_options)
            break
            
    res = requests.put(f"{BASE_URL}/api/resource/DocType/Order Form", json=order_doc, headers=headers)
    print("Order Form DocType update:", res.status_code)

    # 2. Update Workflow
    try:
        workflow = roqson.get_doc("Workflow", "Order Workflow")
        
        # Keep only allowed states
        valid_states = ["Draft", "Needs Review", "Approved", "Canceled", "Cancelled"]
        new_states = [s for s in workflow.get("states", []) if s["state"] in valid_states]
        
        # Ensure 'Approved' exists
        if "Approved" not in [s["state"] for s in new_states]:
            new_states.append({
                "state": "Approved",
                "doc_status": "1",
                "update_field": "workflow_state",
                "update_value": "Approved",
                "allow_edit": "All",
                "doctype": "Workflow Document State"
            })
            
        workflow["states"] = new_states
        
        # Keep only valid transitions
        new_transitions = []
        for t in workflow.get("transitions", []):
            if t["state"] in valid_states and t["next_state"] in valid_states:
                new_transitions.append(t)
                
        # Make sure there is a way to get to Approved from Needs Review
        has_approve = any(t["action"] == "Approve" for t in new_transitions)
        if not has_approve:
            new_transitions.append({
                "state": "Needs Review",
                "action": "Approve",
                "next_state": "Approved",
                "allowed": "Administrator",
                "allow_self_approval": 1,
                "doctype": "Workflow Transition"
            })
            
        workflow["transitions"] = new_transitions
        
        res = requests.put(f"{BASE_URL}/api/resource/Workflow/Order Workflow", json=workflow, headers=headers)
        print("Order Workflow update:", res.status_code)
        if res.status_code != 200:
            print("Workflow error:", res.text)
    except Exception as e:
        print("Error updating workflow:", e)


def update_sales_form():
    sales_doc = roqson.get_doc("DocType", "Sales")
    target_options = [
        "Pending", 
        "Dispatching", 
        "In Transit", 
        "Received", 
        "Failed", 
        "Completed", 
        "Cancelled"
    ]
    
    for f in sales_doc.get("fields", []):
        if f.get("fieldname") == "status":
            f["options"] = "\n".join(target_options)
            f["default"] = "Pending"
            break
            
    res = requests.put(f"{BASE_URL}/api/resource/DocType/Sales", json=sales_doc, headers=headers)
    print("Sales DocType update:", res.status_code)


if __name__ == "__main__":
    update_sales_form()
    update_order_form()
