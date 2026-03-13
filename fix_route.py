import roqson

script_name = "in-form big buttons (preferred) + fallback to toolbar buttons"

script_code = """
frappe.ui.form.on('Trip Ticket', {
  onload_post_render(frm) {
    frm.trigger('render_delivery_buttons');
  },

  refresh(frm) {
    frm.trigger('render_delivery_buttons');
    
    const allowed_roles = ['Administrator', 'System Manager', 'Manager', 'President', 'Stock Manager', 'Stock User', 'Dispatcher', 'Driver'];
    if (allowed_roles.some(role => frappe.user.has_role(role))) {
        frm.add_custom_button(__('Billing Statement'), function() {
            // Try using standard routing without pre-selecting format via arguments
            // We set the format in the global print options
            frappe.route_options = {
                "print_format": "Billing Statement"
            };
            frappe.set_route("print", frm.doc.doctype, frm.doc.name);
        }, __("Print"));
    }
  },

  render_delivery_buttons(frm) {
    const ARRIVAL_FIELD = 'custom_arrival_time';
    const COMPLETION_FIELD = 'custom_completion_time';
    const HTML_FIELD = 'custom_delivery_timeline_controls';

    const tryRender = (attempt = 1) => {
      const htmlField = frm.fields_dict[HTML_FIELD];

      if (!htmlField || !htmlField.$wrapper) {
        if (attempt <= 2) {
          setTimeout(() => tryRender(attempt + 1), 250);
        }
        return;
      }

      const arrival = frm.doc[ARRIVAL_FIELD];
      const completion = frm.doc[COMPLETION_FIELD];
      const is_cancelled = (frm.doc.docstatus === 2);

      const disable_time_in = !!arrival || is_cancelled;
      const disable_time_out = !arrival || !!completion || is_cancelled;

      const arrivalText = arrival ? frappe.datetime.str_to_user(arrival) : '—';
      const completionText = completion ? frappe.datetime.str_to_user(completion) : '—';
      
      const allowed_roles = ['Administrator', 'System Manager', 'Manager', 'President', 'Stock Manager', 'Stock User', 'Dispatcher', 'Driver'];
      const show_print = allowed_roles.some(role => frappe.user.has_role(role));

      htmlField.$wrapper.html(`
        <div style="display:flex; gap:12px; flex-wrap:wrap; align-items:center; margin: 6px 0 10px;">
          <button class="btn btn-primary btn-lg tt-time-in" ${disable_time_in ? 'disabled' : ''} style="min-width:220px;">
            Time In (Arrived)
          </button>
          <button class="btn btn-success btn-lg tt-time-out" ${disable_time_out ? 'disabled' : ''} style="min-width:220px;">
            Time Out (Delivered)
          </button>
          ${show_print ? `
          <button class="btn btn-default btn-lg tt-print-billing" style="min-width:220px; border: 1px solid #d1d8dd;">
            <i class="fa fa-print"></i> Print Billing Statement
          </button>
          ` : ''}
        </div>

        <div style="display:flex; gap:24px; flex-wrap:wrap;">
          <div><b>Arrival Time:</b> ${arrivalText}</div>
          <div><b>Completion Time:</b> ${completionText}</div>
        </div>
      `);

      htmlField.$wrapper.find('.tt-time-in').on('click', () => {
        frappe.confirm('Record Arrival Time now? This cannot be edited by the driver.', async () => {
          await frm.trigger('ensure_saved_then_call_time_api', 'time_in');
        });
      });

      htmlField.$wrapper.find('.tt-time-out').on('click', () => {
        frappe.confirm('Record Completion Time now? This cannot be edited by the driver.', async () => {
          await frm.trigger('ensure_saved_then_call_time_api', 'time_out');
        });
      });
      
      if (show_print) {
          htmlField.$wrapper.find('.tt-print-billing').on('click', () => {
            frappe.route_options = { "print_format": "Billing Statement" };
            frappe.set_route("print", frm.doc.doctype, frm.doc.name);
          });
      }
    };

    tryRender();
  },

  async ensure_saved_then_call_time_api(frm, action) {
    if (frm.is_new()) {
      await frm.save();
    }
    return frm.trigger('call_time_api', action);
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
});
"""

try:
    roqson.update_doc("Client Script", script_name, {"script": script_code, "enabled": 1})
    print(f"Updated script to fix set_route issue")
except Exception as e:
    print(f"Error updating script: {e}")
