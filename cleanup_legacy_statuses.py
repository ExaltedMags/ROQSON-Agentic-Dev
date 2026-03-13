import roqson

# 1. Update Inventory Stock Out
script_name = "Inventory Stock Out"
print(f"Updating {script_name}...")
old_script = roqson.get_script_body('Server Script', script_name)
new_script = old_script.replace('        "Paid": "Out",\n', '')
new_script = new_script.replace('        "Unpaid": "Out"\n', '        "Canceled": "Released" # comma cleanup handled implicitly if next row matches')
# Fixing potential syntax error from removing last item in dict
new_script = new_script.replace('"Rejected": "Released",', '"Rejected": "Released"')
new_script = new_script.replace('"Rejected": "Released"\n    }', '"Rejected": "Released"\n    }')

# Actually let's just do a clean replacement of the map
old_map = """    state_to_movement = {
        "Approved": "Reserved",   # Auto-reserve stock on Approval
        "Reserved": "Reserved",   # Manual Reserve Stock (idempotent, kept for compat)
        "Dispatched": "Out",
        "Delivered": "Out",
        "Delivery Failed": "Return",
        "Redeliver": "Reserved",
        "Canceled": "Released",
        "Rejected": "Released",
        "Paid": "Out",
        "Unpaid": "Out"
    }"""

new_map = """    state_to_movement = {
        "Approved": "Reserved",   # Auto-reserve stock on Approval
        "Reserved": "Reserved",   # Manual Reserve Stock (idempotent, kept for compat)
        "Dispatched": "Out",
        "Delivered": "Out",
        "Delivery Failed": "Return",
        "Redeliver": "Reserved",
        "Canceled": "Released",
        "Rejected": "Released"
    }"""

if old_map in old_script:
    new_script = old_script.replace(old_map, new_map)
    roqson.update_doc('Server Script', script_name, {'script': new_script})
    print(f"Updated {script_name}")
else:
    print(f"Could not find exact map in {script_name}, skipping.")


# 2. Update Notification Script
script_name = "Approved, Rejected, Reserved, Dispatched, Delivered, Delivery Failed, Rescheduled"
print(f"Updating {script_name}...")
old_script = roqson.get_script_body('Server Script', script_name)

old_colors = """    "Unpaid": "#9f1853",
    "Paid": "#1c7a3b"
}"""
new_colors = "}"

if old_colors in old_script:
    new_script = old_script.replace(old_colors, new_colors)
    # Also remove comma from Rescheduled line
    new_script = new_script.replace('"Rescheduled": "#8a3ffc",', '"Rescheduled": "#8a3ffc"')
    roqson.update_doc('Server Script', script_name, {'script': new_script})
    print(f"Updated {script_name}")
else:
    print(f"Could not find legacy colors in {script_name}, skipping.")
