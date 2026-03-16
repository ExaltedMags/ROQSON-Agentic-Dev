const fs = require('fs');
const env = Object.fromEntries(
  fs.readFileSync('.env', 'utf8')
    .split(/\r?\n/)
    .filter(Boolean)
    .map((line) => {
      const idx = line.indexOf('=');
      return [line.slice(0, idx), line.slice(idx + 1)];
    })
);

const script = `trip_ticket = frappe.form_dict.get("trip_ticket")
action = frappe.form_dict.get("action")
if not trip_ticket:
    frappe.throw("trip_ticket is required")
if not action:
    frappe.throw("action is required")
doctype = "Trip Ticket"
field_map = {
    "time_in": "arrival_time",
    "time_out": "completion_time",
    "proof": "proof_time_stamp",
    "signature": "signature_timestamp",
}
field = field_map.get(action)
if not field:
    frappe.throw("Invalid action")

doc = frappe.get_doc(doctype, trip_ticket)
workflow_state = (doc.get("workflow_state") or "").strip()

if action in ["time_in", "time_out"]:
    if workflow_state == "Draft":
        frappe.throw("Dispatch the Trip Ticket first before recording Time In or Time Out.")
    if workflow_state in ["Received", "Failed"]:
        frappe.throw("This Trip Ticket is already completed.")

# FIX: frappe.utils.now() can return un-padded hours like "2:31:48"
# strftime is blocked in safe_exec, so pad manually
now = frappe.utils.now()
parts = now.split(" ", 1)
if len(parts) == 2:
    date_part = parts[0]
    time_part = parts[1]
    time_segs = time_part.split(":")
    time_segs[0] = time_segs[0].zfill(2)
    if "." in time_segs[-1]:
        time_segs[-1] = time_segs[-1].split(".")[0]
    now = date_part + " " + ":".join(time_segs)

media_present_raw = frappe.form_dict.get("media_present")
media_present = str(media_present_raw).lower() in ("1", "true", "yes", "y")

if action == "time_in":
    if doc.get("arrival_time"):
        frappe.throw("Time In already recorded.")
    value = now
    frappe.db.set_value(doctype, trip_ticket, field, value, update_modified=True)
elif action == "time_out":
    if not doc.get("arrival_time"):
        frappe.throw("Time Out requires Time In first.")
    if doc.get("completion_time"):
        frappe.throw("Time Out already recorded.")
    value = now
    frappe.db.set_value(doctype, trip_ticket, field, value, update_modified=True)
elif action in ("proof", "signature"):
    value = now if media_present else None
    frappe.db.set_value(doctype, trip_ticket, field, value, update_modified=True)
else:
    value = now
    frappe.db.set_value(doctype, trip_ticket, field, value, update_modified=True)

new_modified = frappe.db.get_value(doctype, trip_ticket, "modified")
frappe.response["message"] = {
    "field": field,
    "value": value or "",
    "modified": str(new_modified),
}
`;

fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Server%20Script/Timestamping', {
  method: 'PUT',
  headers: {
    Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET,
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({ script })
}).then(async (response) => {
  const text = await response.text();
  console.log(response.status);
  console.log(text);
  if (!response.ok) process.exit(1);
}).catch((error) => {
  console.error(error);
  process.exit(1);
});
