import roqson


COPY_HELPER_BLOCK = """

function roqson_add_copy_action(listview, doctype, label) {
    if (!Array.isArray(frappe.user_roles) || frappe.user_roles.indexOf("System Manager") === -1) {
        return;
    }
    if (listview.__roqson_copy_action_added) {
        return;
    }
    listview.__roqson_copy_action_added = true;

    listview.page.add_action_item("Copy to New Draft", function() {
        var selected = listview.get_checked_items() || [];
        if (selected.length !== 1) {
            frappe.msgprint("Select exactly one " + label + " record to copy.");
            return;
        }
        if (!frappe.model || typeof frappe.model.copy_doc !== "function") {
            frappe.msgprint("Copying is not available in this ERPNext build.");
            return;
        }

        frappe.dom.freeze("Preparing draft copy...");
        frappe.model.with_doctype(doctype, function() {
            frappe.db.get_doc(doctype, selected[0].name).then(function(source_doc) {
                var copied_doc = frappe.model.copy_doc(source_doc);
                roqson_prepare_copied_doc(copied_doc);
                frappe.dom.unfreeze();
                frappe.show_alert({
                    message: "Draft copy opened. Review linked references before saving.",
                    indicator: "blue"
                });
                frappe.set_route("Form", doctype, copied_doc.name);
            }).catch(function(err) {
                frappe.dom.unfreeze();
                console.error(err);
                frappe.msgprint("Unable to copy " + label + ".");
            });
        });
    });
}

function roqson_prepare_copied_doc(doc) {
    if (!doc) {
        return;
    }
    delete doc.workflow_state;
    delete doc.status;
    delete doc.docstatus;
    delete doc.amended_from;
}
"""


TARGETS = [
    {
        "doctype": "Order Form",
        "script_name": "Order Form List - Master",
        "hook": '    onload(listview) {\n',
        "insertion": '    onload(listview) {\n        roqson_add_copy_action(listview, "Order Form", "Order Form");\n',
    },
    {
        "doctype": "Trip Ticket",
        "script_name": "Archive Trip Ticket List",
        "hook": "    listview.__tt_initialized = true;\n",
        "insertion": '    listview.__tt_initialized = true;\n    roqson_add_copy_action(listview, "Trip Ticket", "Trip Ticket");\n',
    },
    {
        "doctype": "Sales",
        "script_name": "Sales List Script",
        "hook": '    onload: function(listview) {\n',
        "insertion": '    onload: function(listview) {\n        roqson_add_copy_action(listview, "Sales", "Sales");\n',
    },
]


def build_updated_script(current_script, hook, insertion):
    updated = current_script

    if "function roqson_add_copy_action" not in updated:
        updated = updated.rstrip() + COPY_HELPER_BLOCK

    if insertion.strip() not in updated:
        if hook not in updated:
            raise ValueError("Hook not found in current script.")
        updated = updated.replace(hook, insertion, 1)

    return updated


def main(apply_changes=False):
    for target in TARGETS:
        current_script = roqson.get_script_body("Client Script", target["script_name"])
        updated_script = build_updated_script(current_script, target["hook"], target["insertion"])

        if current_script.strip() == updated_script.strip():
            print("[SKIP] " + target["script_name"] + " already includes the copy action.")
            continue

        roqson._show_diff(current_script, updated_script, target["script_name"])

        if apply_changes:
            roqson.update_doc("Client Script", target["script_name"], {"script": updated_script})
            print("[APPLIED] " + target["script_name"])


if __name__ == "__main__":
    import sys
    main(apply_changes="--apply" in sys.argv)
