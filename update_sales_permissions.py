import roqson

script_name = "Sales: Paid Validation"
print(f"Updating {script_name} to grant more roles permission to Create Trip Ticket...")

old_script = roqson.get_script_body('Client Script', script_name)

# Update the role check logic
# Old line: if (frappe.user_roles.includes('Dispatch') || frappe.user_roles.includes('Administrator')) {
new_role_check = "if (frappe.user_roles.includes('Dispatch') || frappe.user_roles.includes('Administrator') || frappe.user_roles.includes('System Manager') || frappe.user_roles.includes('Manager') || frappe.user_roles.includes('President')) {"

new_script = old_script.replace(
    "if (frappe.user_roles.includes('Dispatch') || frappe.user_roles.includes('Administrator')) {",
    new_role_check
)

if old_script != new_script:
    roqson.update_doc('Client Script', script_name, {'script': new_script})
    print("Update complete.")
else:
    print("Could not find the role check line or it was already updated.")
