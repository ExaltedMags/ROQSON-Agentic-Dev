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

(async () => {
  const res = await fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Client%20Script/Full%20Order%20Script', {
    headers: { Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET }
  });
  const data = (await res.json()).data;
  let script = data.script;

  if (!script.includes('const HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", "Mark Delivered", "Mark Delivery Failed"];')) {
    throw new Error('constant block not found');
  }

  script = script.replace(
    'const HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", "Mark Delivered", "Mark Delivery Failed"];',
    'const AUTO_FINALIZABLE_WORKFLOW_STATES = ["In Transit", "Arrived", "Delivered"];\nconst AUTO_RECEIVE_ACTION = "Mark Delivered";\nconst AUTO_FAIL_ACTION = "Mark Delivery Failed";\nconst HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", AUTO_RECEIVE_ACTION, AUTO_FAIL_ACTION];'
  );

  const marker = 'function hide_redundant_workflow_actions(frm) {';
  const insert = `function get_auto_finalize_action(frm) {\n\n  const workflow_state = (frm.doc?.workflow_state || "").trim();\n\n  const delivery_status = (frm.doc?.[DELIVERY_STATUS_FIELD] || "").trim();\n\n  if (!AUTO_FINALIZABLE_WORKFLOW_STATES.includes(workflow_state)) return "";\n\n  if (!frm.doc?.[ARRIVAL_TIME_FIELD]) return "";\n\n  if (!frm.doc?.[COMPLETION_TIME_FIELD]) return "";\n\n  if (delivery_status === "Successful") return AUTO_RECEIVE_ACTION;\n\n  if (delivery_status === FAILED_STATUS_VALUE) return AUTO_FAIL_ACTION;\n\n  return "";\n\n}\n\nasync function auto_finalize_trip_ticket(frm) {\n\n  const action = get_auto_finalize_action(frm);\n\n  if (!action || frm.__auto_finalize_running) return;\n\n  frm.__auto_finalize_running = true;\n\n  try {\n\n    await frappe.call({\n\n      method: "frappe.model.workflow.apply_workflow",\n\n      args: {\n\n        doc: frm.doc,\n\n        action: action,\n\n      },\n\n      freeze: true,\n\n      freeze_message: "Finalizing trip ticket...",\n\n    });\n\n    await frm.reload_doc();\n\n  } finally {\n\n    frm.__auto_finalize_running = false;\n\n    hide_redundant_workflow_actions(frm);\n\n  }\n\n}\n\n`;
  script = script.replace(marker, insert + marker);

  const afterSaveOld = `  async after_save(frm) {\n\n    normalize_all_time_fields(frm);\n\n    await refresh_taken_orders_cache(frm);\n\n    hide_redundant_workflow_actions(frm);\n\n    update_parent_visibility(frm);\n\n    update_saved_only_visibility(frm);\n\n    update_timestamp_visibility_saved_and_has_value(frm);\n\n    set_order_query(frm);\n\n  },`;
  const afterSaveNew = `  async after_save(frm) {\n\n    normalize_all_time_fields(frm);\n\n    await refresh_taken_orders_cache(frm);\n\n    hide_redundant_workflow_actions(frm);\n\n    update_parent_visibility(frm);\n\n    update_saved_only_visibility(frm);\n\n    update_timestamp_visibility_saved_and_has_value(frm);\n\n    set_order_query(frm);\n\n    await auto_finalize_trip_ticket(frm);\n\n  },`;
  if (!script.includes(afterSaveOld)) {
    throw new Error('after_save block not found');
  }
  script = script.replace(afterSaveOld, afterSaveNew);

  const put = await fetch('https://roqson-industrial-sales.s.frappe.cloud/api/resource/Client%20Script/Full%20Order%20Script', {
    method: 'PUT',
    headers: {
      Authorization: 'token ' + env.ROQSON_API_KEY + ':' + env.ROQSON_API_SECRET,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ script })
  });
  const text = await put.text();
  console.log(put.status);
  console.log(text);
  if (!put.ok) process.exit(1);
})();
