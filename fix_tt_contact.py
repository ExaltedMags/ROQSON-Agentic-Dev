import roqson
import json

docfield_name = "6mgqkllcua"
update_data = {
    "reqd": 0,
    "read_only": 0,
    "options": ""
}

print(f"Updating DocField {docfield_name}...")
roqson.update_doc("DocField", docfield_name, update_data)

print("Clearing cache...")
# Normally clear_cache is needed after DocType/DocField changes
try:
    roqson.call_method("frappe.clear_cache")
    print("Cache cleared.")
except Exception as e:
    print(f"Note: Cache clear call might have failed (sometimes restricted), but the DB update is done: {e}")
