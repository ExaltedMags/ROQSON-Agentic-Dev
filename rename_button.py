import roqson

script_name = "Sales: Form Logic & Calculations"
old_script = roqson.get_script_body("Client Script", script_name)

new_script = old_script.replace(
    "grid.add_custom_button(__('Toggle Unreserve Selected'), () => {",
    "grid.add_custom_button(__('Unreserve Selected'), () => {"
)

roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
