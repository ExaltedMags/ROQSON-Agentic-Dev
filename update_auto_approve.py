import roqson

script_name = "Auto Approve"
doc = roqson.get_doc("Server Script", script_name)
current_script = doc.get("script", "")

old_block = """
            # Auto-reserve: no modifications, immediately move to Reserved
            try:
                frappe.call(
                    "frappe.model.workflow.apply_workflow",
                    doc=wf,
                    action="Reserve Stock"
                )
            except Exception:
                frappe.db.set_value("Order Form", doc.name, "workflow_state",
                                    "Reserved", update_modified=False)"""

if old_block in current_script:
    new_script = current_script.replace(old_block, "")
    roqson.update_doc("Server Script", script_name, {"script": new_script})
    print("Auto Approve script updated successfully.")
else:
    print("Could not find the exact block to remove. It might have already been modified.")
