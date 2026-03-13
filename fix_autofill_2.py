import roqson
import re

script_name = "Full Order Script"
old_script = roqson.get_script_body("Client Script", script_name)

# 1. Replace the array element in get_order_doc_cached
new_script = re.sub(
    r'ORDER_CONTACT_PERSON_FIELD,\s*ORDER_PREFERRED_DATETIME_FIELD,?',
    r'ORDER_CONTACT_PERSON_FIELD,\n          ORDER_PREFERRED_DATE_FIELD,\n          ORDER_PREFERRED_TIME_FIELD,',
    old_script
)

# 2. Replace the extraction logic in handle_order_selected
old_logic = r'// Split the order\'s preferred_delivery_date_and_time into separate date and time\s*const preferred_datetime_raw = order_doc\?\.\[ORDER_PREFERRED_DATETIME_FIELD\] \|\| "";\s*const preferred_date_from_order = preferred_datetime_raw \? preferred_datetime_raw\.split\(" "\)\[0\] : "";\s*const preferred_time_from_order = \(preferred_datetime_raw && preferred_datetime_raw\.includes\(" "\)\) \? preferred_datetime_raw\.split\(" "\)\[1\] : "";'

new_logic = """// Get the preferred date and time directly from the order doc
    const preferred_date_from_order = order_doc?.[ORDER_PREFERRED_DATE_FIELD] || "";
    const preferred_time_from_order = order_doc?.[ORDER_PREFERRED_TIME_FIELD] || "";"""

new_script = re.sub(old_logic, new_logic, new_script)

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
