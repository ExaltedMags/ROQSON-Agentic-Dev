import roqson

script_name = "Auto Approve"
print(f"Updating {script_name}...")

old_script = roqson.get_script_body('Server Script', script_name)

# 1. Update status from Unpaid to Pending
new_script = old_script.replace('"status": "Unpaid"', '"status": "Pending"')

# 2. Map fulfillment_type from Order Form to Sales
# Finding the right place to insert - after status
if '"fulfillment_type"' not in new_script:
    new_script = new_script.replace(
        '"status": "Pending",',
        '"status": "Pending",\n                    "fulfillment_type": doc.get("fulfillment_type") or "Delivery",'
    )

roqson.update_doc('Server Script', script_name, {'script': new_script})
print("Update complete.")
