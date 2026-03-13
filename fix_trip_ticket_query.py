import roqson

script_name = "Full Order Script"
print(f"Updating {script_name}...")

old_script = roqson.get_script_body('Client Script', script_name)

# Update ALLOWED_STATUSES
new_script = old_script.replace('const ALLOWED_STATUSES = ["Unpaid"];', 'const ALLOWED_STATUSES = ["Pending"];')

if old_script != new_script:
    roqson.update_doc('Client Script', script_name, {'script': new_script})
    print("Update complete.")
else:
    print("Could not find ALLOWED_STATUSES line or already updated.")

# Also disable the redundant "Trip Ticket Filter" script
print("Disabling redundant Trip Ticket Filter script...")
try:
    roqson.update_doc('Client Script', 'Trip Ticket Filter', {'enabled': 0})
    print("Disabled Trip Ticket Filter.")
except Exception as e:
    print(f"Note: Could not disable Trip Ticket Filter: {e}")
