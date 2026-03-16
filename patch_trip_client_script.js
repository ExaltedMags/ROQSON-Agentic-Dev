const fs = require('fs');
let script = fs.readFileSync('tmp_full_order_script_live.js', 'utf8');
script = script.replace('const AUTO_FINALIZABLE_WORKFLOW_STATES = ["In Transit", "Arrived", "Delivered"];\nconst AUTO_RECEIVE_ACTION = "Mark Delivered";\nconst AUTO_FAIL_ACTION = "Mark Delivery Failed";\nconst HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", AUTO_RECEIVE_ACTION, AUTO_FAIL_ACTION];','const HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", "Mark Delivered", "Mark Delivery Failed"];');
const oldBlock = `function hide_redundant_workflow_actions(frm) {

  if (!frm?.page) return;

  const removeButtons = function () {

    for (const label of HIDDEN_WORKFLOW_ACTIONS) {

      if (typeof frm.remove_custom_button === "function") {

        frm.remove_custom_button(label);

        frm.remove_custom_button(label, "Actions");

        frm.remove_custom_button(label, __("Actions"));

      }

      if (frm.page && typeof frm.page.remove_inner_button === "function") {

        frm.page.remove_inner_button(label);

        frm.page.remove_inner_button(label, "Actions");

        frm.page.remove_inner_button(label, __("Actions"));

      }

    }

  };

  removeButtons();

  setTimeout(removeButtons, 100);

  setTimeout(removeButtons, 400);

}

function get_auto_finalize_action(frm) {

  const workflow_state = (frm.doc?.workflow_state || "").trim();

  const delivery_status = (frm.doc?.[DELIVERY_STATUS_FIELD] || "").trim();

  if (!AUTO_FINALIZABLE_WORKFLOW_STATES.includes(workflow_state)) return "";

  if (!frm.doc?.[ARRIVAL_TIME_FIELD]) return "";

  if (!frm.doc?.[COMPLETION_TIME_FIELD]) return "";

  if (delivery_status === "Successful") return AUTO_RECEIVE_ACTION;

  if (delivery_status === FAILED_STATUS_VALUE) return AUTO_FAIL_ACTION;

  return "";

}

async function auto_finalize_trip_ticket(frm) {

  const action = frm.__auto_finalize_action || "";

  frm.__auto_finalize_action = "";

  if (!action || frm.__auto_finalize_running) return;

  frm.__auto_finalize_running = true;

  try {

    await frappe.call({

      method: "frappe.model.workflow.apply_workflow",

      args: {

        doc: frm.doc,

        action: action,

      },

      freeze: true,

      freeze_message: "Finalizing trip ticket...",

    });

    await frm.reload_doc();

  } finally {

    frm.__auto_finalize_running = false;

    hide_redundant_workflow_actions(frm);

  }

}`;
const newBlock = `function hide_redundant_workflow_actions(frm) {

  if (!frm?.page) return;

  const removeButtons = function () {

    for (const label of HIDDEN_WORKFLOW_ACTIONS) {

      if (typeof frm.remove_custom_button === "function") {

        frm.remove_custom_button(label);

        frm.remove_custom_button(label, "Actions");

        frm.remove_custom_button(label, __("Actions"));

      }

      if (frm.page && typeof frm.page.remove_inner_button === "function") {

        frm.page.remove_inner_button(label);

        frm.page.remove_inner_button(label, "Actions");

        frm.page.remove_inner_button(label, __("Actions"));

      }

    }

    $(frm.page.wrapper).find("a, button, .dropdown-item").each(function () {

      const text = ($(this).text() || "").trim();

      if (HIDDEN_WORKFLOW_ACTIONS.includes(text)) {

        $(this).hide();

        $(this).closest("li").hide();

      }

    });

  };

  removeButtons();

  setTimeout(removeButtons, 100);

  setTimeout(removeButtons, 400);

}`;
script = script.replace(oldBlock, newBlock);
script = script.replace('function update_saved_only_visibility(frm) {\n\n  const is_saved = !frm.is_new();','function update_saved_only_visibility(frm) {\n\n  const is_saved = !frm.is_new() && (frm.doc?.workflow_state || "") !== "Draft";');
script = script.replace('  before_save(frm) {\n\n    frm.__auto_finalize_action = get_auto_finalize_action(frm);\n\n  },\n\n','');
script = script.replace('    await auto_finalize_trip_ticket(frm);\n\n','');
fs.writeFileSync('tmp_full_order_script_live.js', script);
console.log('patched');
