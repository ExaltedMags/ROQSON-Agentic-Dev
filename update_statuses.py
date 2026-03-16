import roqson
import json
import os
import requests

key = os.environ.get("ROQSON_API_KEY")
secret = os.environ.get("ROQSON_API_SECRET")
headers = {"Authorization": f"token {key}:{secret}"}

# 1. Update Order Form workflow_state options
order_doctype = roqson.get_doc("DocType", "Order Form")
for f in order_doctype.get("fields", []):
    if f.get("fieldname") == "workflow_state":
        options = f.get("options", "").split("\n")
        if "In Transit" not in options:
            options.append("In Transit")
        if "Received" not in options:
            options.append("Received")
        f["options"] = "\n".join(options)
        break

try:
    res = requests.put(f"https://roqson-industrial-sales.s.frappe.cloud/api/resource/DocType/Order Form", json=order_doctype, headers=headers)
    print("Order Form options update:", res.status_code)
except Exception as e:
    print("Order Form update error:", e)

# 2. Update Sales status options
sales_doctype = roqson.get_doc("DocType", "Sales")
for f in sales_doctype.get("fields", []):
    if f.get("fieldname") == "status":
        options = f.get("options", "").split("\n")
        if "Completed" not in options:
            options.append("Completed")
        f["options"] = "\n".join(options)
        break

try:
    res = requests.put(f"https://roqson-industrial-sales.s.frappe.cloud/api/resource/DocType/Sales", json=sales_doctype, headers=headers)
    print("Sales options update:", res.status_code)
except Exception as e:
    print("Sales update error:", e)
