import roqson

script_content = """
invalid_orders = frappe.get_all("Order Form", filters={"docstatus": 2}, fields=["name", "workflow_state"])
count = 0
for order in invalid_orders:
    if order.workflow_state != "Canceled":
        frappe.db.set_value("Order Form", order.name, "workflow_state", "Canceled")
        count += 1
frappe.response["message"] = f"Updated {count} cancelled orders to Canceled state."
"""

print("Creating temporary server script...")
try:
    roqson.call_method("frappe.client.insert", doc={
        "doctype": "Server Script",
        "name": "update_invalid_orders_status",
        "script_type": "API",
        "api_method": "update_invalid_orders_status",
        "allow_guest": 0,
        "script": script_content
    })
    print("Script created successfully.")
except Exception as e:
    print(f"Error creating script: {e}")
    # Might already exist
    pass

print("Calling API method...")
try:
    res = roqson.call_method("update_invalid_orders_status")
    print(res)
except Exception as e:
    print(f"Error calling method: {e}")

print("Disabling temporary server script...")
try:
    # Actually delete it instead of disabling
    roqson.call_method("frappe.client.delete", doctype="Server Script", name="update_invalid_orders_status")
    print("Script deleted.")
except Exception as e:
    print(f"Error deleting script: {e}")
