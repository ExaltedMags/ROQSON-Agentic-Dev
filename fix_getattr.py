import roqson

script_name = "Sales Inventory Stock Out"
old_script = roqson.get_script_body("Server Script", script_name)

new_script = old_script.replace(
    "getattr(item, 'is_unreserved', 0)",
    "item.get('is_unreserved') or 0"
)

roqson.safe_update_script("Server Script", script_name, new_script, auto_confirm=True)
