import roqson

script_name = "renders buttons inside the HTML field"
new_script = """frappe.ui.form.on('Trip Ticket', {
  refresh(frm) {
    frm.trigger('render_delivery_timeline_buttons');
  },

  render_delivery_timeline_buttons(frm) {
    const ARRIVAL_FIELD = 'custom_arrival_time';
    const COMPLETION_FIELD = 'custom_completion_time';
    const HTML_FIELD = 'custom_delivery_timeline_controls';

    const htmlField = frm.fields_dict[HTML_FIELD];
    if (!htmlField || !htmlField.$wrapper) return;

    const isNew = frm.is_new();
    const isCancelled = (frm.doc.docstatus === 2);
    const wf = frm.doc.workflow_state;

    const arrival = frm.doc[ARRIVAL_FIELD];
    const completion = frm.doc[COMPLETION_FIELD];

    // Button Logic
    const disableDispatch = isNew || isCancelled || wf !== 'Draft';
    const disableIn = isNew || isCancelled || wf !== 'In Transit' || !!arrival;
    const disableOut = isNew || isCancelled || wf !== 'Arrived' || !!completion;

    const arrivalText = arrival ? frappe.datetime.str_to_user(arrival) : '—';
    const completionText = completion ? frappe.datetime.str_to_user(completion) : '—';

    htmlField.$wrapper.html(`
      <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin: 6px 0 10px;">
        <button class="btn btn-info btn-lg tt-dispatch" ${disableDispatch ? 'disabled' : ''} style="min-width:180px;">
          Dispatch (In Transit)
        </button>
        <button class="btn btn-primary btn-lg tt-time-in" ${disableIn ? 'disabled' : ''} style="min-width:180px;">
          Time In (Arrived)
        </button>
        <button class="btn btn-success btn-lg tt-time-out" ${disableOut ? 'disabled' : ''} style="min-width:180px;">
          Time Out (Delivered)
        </button>
      </div>

      <div style="display:flex; gap:24px; flex-wrap:wrap; margin-top: 8px;">
        <div><b>Status:</b> <span class="label ${wf === 'Draft' ? 'label-default' : (wf === 'In Transit' ? 'label-info' : (wf === 'Arrived' ? 'label-primary' : 'label-success'))}">${wf || 'Draft'}</span></div>
        <div><b>Arrival Time:</b> ${arrivalText}</div>
        <div><b>Completion Time:</b> ${completionText}</div>
      </div>

      ${isNew ? `<div style="margin-top:8px; opacity:.75;">Save this Trip Ticket first to enable delivery controls.</div>` : ``}
    `);

    htmlField.$wrapper.find('.tt-dispatch').on('click', () => {
      frappe.confirm(__('Start delivery run and set status to In Transit?'), () => {
        frm.trigger('call_time_api', 'dispatch');
      });
    });

    htmlField.$wrapper.find('.tt-time-in').on('click', () => {
      frappe.confirm(__('Record Arrival Time now?'), () => {
        frm.trigger('call_time_api', 'time_in');
      });
    });

    htmlField.$wrapper.find('.tt-time-out').on('click', () => {
      frappe.confirm(__('Record Completion Time now?'), () => {
        frm.trigger('call_time_api', 'time_out');
      });
    });
  },

  call_time_api(frm, action) {
    return frappe.call({
      method: 'trip_ticket_time_action',
      args: {
        trip_ticket: frm.doc.name,
        action: action
      }
    }).then(() => frm.reload_doc());
  }
});"""

roqson.safe_update_script('Client Script', script_name, new_script, auto_confirm=True)
