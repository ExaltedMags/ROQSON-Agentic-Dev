import roqson
import re

script_name = "Full Order Script"
old_script = roqson.get_script_body("Client Script", script_name)

new_script = re.sub(
    r'for\s*\(\s*const\s+f\s+of\s+supplement\s*\)\s*\{\s*if\s*\(\s*sales_doc\[f\]\s*==\s*null\s*&&\s*order_doc\[f\]\s*!=\s*null\s*\)\s*sales_doc\[f\]\s*=\s*order_doc\[f\];\s*\}',
    """for (const f of supplement) {
          if (!sales_doc[f] && order_doc[f]) sales_doc[f] = order_doc[f];
        }""",
    old_script
)

if new_script != old_script:
    roqson.safe_update_script("Client Script", script_name, new_script, auto_confirm=True)
    print("Script updated successfully.")
else:
    print("Could not find the loop to replace via regex.")
