import roqson
import json

script_name = "Full Order Script"
doc = roqson.get_doc("Client Script", script_name)
content = doc["script"]

# Fix 1: Update update_parent_visibility to ensure contact/address fields are shown
old_fn = """function update_parent_visibility(frm) {

  if (has_df(frm, PROOF_TS_FIELD)) {

    frm.toggle_display(PROOF_TS_FIELD, !!frm.doc?.[PROOF_FIELD] || !!frm.doc?.[PROOF_TS_FIELD]);

  }"""

new_fn = """function update_parent_visibility(frm) {

  // Ensure contact and address fields are always visible if they exist
  [TRIP_CONTACT_FIELD, TRIP_CONTACT_PERSON_FIELD, TRIP_ADDRESS_FIELD].forEach(f => {
    if (has_df(frm, f)) frm.toggle_display(f, true);
  });

  if (has_df(frm, PROOF_TS_FIELD)) {

    frm.toggle_display(PROOF_TS_FIELD, !!frm.doc?.[PROOF_FIELD] || !!frm.doc?.[PROOF_TS_FIELD]);

  }"""

# Fix 2: Improve has_df to be more robust
old_has_df = """function has_df(frm, fieldname) {

  return !!frappe.meta.get_docfield(frm.doctype, fieldname, frm.doc.name);

}"""

new_has_df = """function has_df(frm, fieldname) {
  if (!fieldname) return false;
  return !!frappe.meta.get_docfield(frm.doctype, fieldname, frm.doc.name) || 
         (frm.fields_dict && !!frm.fields_dict[fieldname]);
}"""

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    print("Updated update_parent_visibility")
else:
    print("Could not find update_parent_visibility to replace")

if old_has_df in content:
    content = content.replace(old_has_df, new_has_df)
    print("Updated has_df")
else:
    print("Could not find has_df to replace")

if content != doc["script"]:
    roqson.safe_update_script("Client Script", script_name, content)
else:
    print("No changes made to script content.")
