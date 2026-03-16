import roqson

def update_script(name, old_str, new_str):
    doc = roqson.get_doc("Server Script", name)
    script = doc.get("script", "")
    if old_str in script:
        new_script = script.replace(old_str, new_str)
        roqson.update_doc("Server Script", name, {"script": new_script})
        print(f"Updated: {name}")
    else:
        print(f"No changes needed or string not found in: {name}")

# Fix Auto Create Sales
update_script(
    "Auto Create Sales on Approval",
    'if doc.workflow_state != "Approved" or old_wf == "Approved":',
    'if doc.workflow_state != "Reserved" or old_wf == "Reserved":'
)

# Fix Inventory Stock Out
update_script(
    "Inventory Stock Out",
    'if doc.workflow_state == "Approved" and state_changed:',
    'if doc.workflow_state == "Reserved" and state_changed:'
)
