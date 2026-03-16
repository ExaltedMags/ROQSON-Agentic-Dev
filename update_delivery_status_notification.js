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

const script = `# DocType Event Server Script (Before Save)
# Enforces Trip Ticket delivery sequencing and finalizes the workflow on save

table_field = "table_cpme"
workflow_field = "workflow_state"
status_field = "delivery_status"
arrival_field = "arrival_time"
completion_field = "completion_time"

workflow_state = (doc.get(workflow_field) or "").strip()
delivery_status = (doc.get(status_field) or "").strip()
arrival_time = doc.get(arrival_field)
completion_time = doc.get(completion_field)

if workflow_state == "Draft":
    if arrival_time or completion_time or delivery_status:
        frappe.throw("Dispatch the Trip Ticket first before recording Time In, Time Out, or Delivery Status.")

if completion_time and not arrival_time:
    frappe.throw("Time Out requires Time In first.")

if delivery_status and not completion_time:
    frappe.throw("Delivery Status can only be set after Time Out is recorded.")

target_state = ""
sales_target_status = ""

if workflow_state in ["In Transit", "Arrived", "Delivered"] and arrival_time and completion_time:
    if delivery_status == "Successful":
        target_state = "Received"
        sales_target_status = "Received"
    elif delivery_status == "Failed":
        target_state = "Failed"
        sales_target_status = "Failed"

if target_state and workflow_state != target_state:
    doc.set(workflow_field, target_state)

old = doc.get_doc_before_save()
old_wf = (old.get(workflow_field) or "").strip() if old else ""

if sales_target_status and old_wf != target_state and doc.get(table_field):
    for row in doc.get(table_field):
        if row.sales_no:
            frappe.db.set_value("Sales", row.sales_no, "status", sales_target_status)
`;

fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Server%20Script/Delivery%20Status%20Notification', {
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
