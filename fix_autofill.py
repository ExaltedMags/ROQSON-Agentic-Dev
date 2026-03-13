import roqson

script_name = "Full Order Script"
old_script = roqson.get_script_body("Client Script", script_name)

new_script = old_script.replace(
    'const ORDER_PREFERRED_DATETIME_FIELD = "preferred_delivery_date_and_time";',
    'const ORDER_PREFERRED_DATE_FIELD = "preferred_delivery_date";\nconst ORDER_PREFERRED_TIME_FIELD = "preferred_delivery_time";'
)

new_script = new_script.replace(
    """          ORDER_CONTACT_PERSON_FIELD,
          ORDER_PREFERRED_DATETIME_FIELD,""",
    """          ORDER_CONTACT_PERSON_FIELD,
          ORDER_PREFERRED_DATE_FIELD,
          ORDER_PREFERRED_TIME_FIELD,"""
)

# In handle_order_selected:
old_date_logic = """    // Split the order's preferred_delivery_date_and_time into separate date and time
    const preferred_datetime_raw = order_doc?.[ORDER_PREFERRED_DATETIME_FIELD] || "";
    const preferred_date_from_order = preferred_datetime_raw ? preferred_datetime_raw.split(" ")[0] : "";
    const preferred_time_from_order = (preferred_datetime_raw && preferred_datetime_raw.includes(" ")) ? preferred_datetime_raw.split(" ")[1] : "";"""

new_date_logic = """    // Get the preferred date and time directly from the order doc
    const preferred_date_from_order = order_doc?.[ORDER_PREFERRED_DATE_FIELD] || "";
    const preferred_time_from_order = order_doc?.[ORDER_PREFERRED_TIME_FIELD] || "";"""

new_script = new_script.replace(old_date_logic, new_date_logic)

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
