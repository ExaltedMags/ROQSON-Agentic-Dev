// -- Order Form: Edit Mode Control -------------------------------------------
// Post-Draft forms appear read-only to Administrator, Manager, System Manager,
// and President roles. An 'Edit' button activates full edit mode for that
// session. Read-only view resets automatically after each save.
// Draft forms are not touched — default Frappe behavior applies.
//
// Implementation notes:
//   docstatus=0 (Draft): fields editable by default. No action needed.
//   docstatus=1 (Submitted/post-Draft): Frappe's native submitted-doc protection
//     locks ALL fields unless df.allow_on_submit=1. set_df_property('read_only',0)
//     alone does nothing. We must also set allow_on_submit=1 when unlocking, and
//     restore allow_on_submit=0 when re-locking.
//   docstatus=0 post-Draft (rare): manual read_only approach used.

frappe.ui.form.on('Order Form', {
    onload(frm) {
        // Only reset the flag here. Locking is handled exclusively in refresh
        // to avoid a double-lock (onload fires just before refresh, which would
        // cause the second lock to see all fields already read_only and populate
        // _roqson_locked_fields as empty, making Edit restore nothing).
        frm._roqson_edit_mode = false;
    },
    refresh(frm) {
        apply_edit_mode_control(frm);
    },
    after_save(frm) {
        frm._roqson_edit_mode = false;
    }
});

var EDIT_ROLES = ['Administrator', 'Manager', 'System Manager', 'President'];
var SKIP_TYPES = ['Section Break', 'Column Break', 'Tab Break', 'HTML', 'Heading', 'Button'];

// For docstatus=0 post-Draft: tracks fields we flipped read_only 0->1
var _roqson_locked_fields = null;
var _roqson_locked_grids  = null;

// For docstatus=1: tracks fields we set allow_on_submit=1 on (so we can restore)
var _roqson_aos_fields = null;
var _roqson_aos_grids  = null;

// Set true when Edit is clicked — causes the next refresh (after reload_doc) to
// enter edit mode instead of re-locking. Persists across the reload cycle.
var _roqson_pending_edit_after_reload = false;

function can_edit_post_draft() {
    return EDIT_ROLES.some(function(r) { return frappe.user.has_role(r); });
}

function apply_edit_mode_control(frm) {
    if (frm._roqson_edit_btn) {
        frm._roqson_edit_btn.remove();
        delete frm.custom_buttons[__('Edit')];
        frm._roqson_edit_btn = null;
    }

    var state = frm.doc.workflow_state;

    if (!state || state === 'Draft') {
        // Restore any meta mutations we made on a previous post-Draft view
        restore_locked_fields(frm);
        restore_allow_on_submit(frm);
        return;
    }

    if (!can_edit_post_draft()) return;

    // If Edit was clicked and a reload was triggered, enter edit mode on fresh data
    if (_roqson_pending_edit_after_reload) {
        _roqson_pending_edit_after_reload = false;
        frm._roqson_edit_mode = true;
        unlock_form(frm);
        return;
    }

    if (frm._roqson_edit_mode) return;

    lock_form(frm);
    add_edit_button(frm);
}

// ── Locking ────────────────────────────────────────────────────────────────

function lock_form(frm) {
    if (frm.doc.docstatus === 1) {
        // Frappe already locks submitted docs natively — just ensure any previous
        // allow_on_submit edits are reversed so the form shows as read-only
        restore_allow_on_submit(frm);
        frm.disable_save();
    } else {
        // docstatus=0 post-Draft: manually flip read_only 0->1
        lock_fields_readonly(frm);
    }
}

function lock_fields_readonly(frm) {
    _roqson_locked_fields = [];
    _roqson_locked_grids  = [];

    frm.fields.forEach(function(field) {
        if (SKIP_TYPES.includes(field.df.fieldtype)) return;
        if (field.df.read_only) return;
        frm.set_df_property(field.df.fieldname, 'read_only', 1);
        frm.refresh_field(field.df.fieldname);
        _roqson_locked_fields.push(field.df.fieldname);
    });

    Object.keys(frm.fields_dict).forEach(function(fieldname) {
        var fd = frm.fields_dict[fieldname];
        if (!fd || !fd.grid) return;
        if (fd.grid.df.read_only) return;
        fd.grid.cannot_add_rows = true;
        fd.grid.cannot_delete_rows = true;
        fd.grid.df.read_only = 1;
        if (fd.grid.wrapper) {
            fd.grid.wrapper.find('.grid-add-row, .grid-add-multiple-rows').hide();
            fd.grid.wrapper.find('.grid-remove-rows').hide();
        }
        fd.grid.refresh();
        _roqson_locked_grids.push(fieldname);
    });

    frm.disable_save();
}

// ── Unlocking ──────────────────────────────────────────────────────────────

function unlock_form(frm) {
    if (frm.doc.docstatus === 1) {
        unlock_submitted(frm);
    } else {
        restore_locked_fields(frm);
    }
}

function unlock_submitted(frm) {
    // For submitted docs, we need allow_on_submit=1 AND read_only=0
    _roqson_aos_fields = [];
    _roqson_aos_grids  = [];

    frm.fields.forEach(function(field) {
        if (SKIP_TYPES.includes(field.df.fieldtype)) return;

        var changed = false;

        if (!field.df.allow_on_submit) {
            field.df.allow_on_submit = 1;
            changed = true;
        }
        // Also clear any read_only that may have been set
        if (field.df.read_only) {
            field.df.read_only = 0;
        }

        frm.refresh_field(field.df.fieldname);
        if (changed) _roqson_aos_fields.push(field.df.fieldname);
    });

    Object.keys(frm.fields_dict).forEach(function(fieldname) {
        var fd = frm.fields_dict[fieldname];
        if (!fd || !fd.grid) return;

        var changed = false;
        if (!fd.grid.df.allow_on_submit) {
            fd.grid.df.allow_on_submit = 1;
            changed = true;
        }
        fd.grid.df.read_only = 0;
        fd.grid.cannot_add_rows = false;
        fd.grid.cannot_delete_rows = false;
        if (fd.grid.wrapper) {
            fd.grid.wrapper.find('.grid-add-row, .grid-add-multiple-rows').show();
            fd.grid.wrapper.find('.grid-remove-rows').show();
        }
        fd.grid.refresh();
        if (changed) _roqson_aos_grids.push(fieldname);
    });

    frm.enable_save();
}

function restore_allow_on_submit(frm) {
    if (_roqson_aos_fields) {
        _roqson_aos_fields.forEach(function(fieldname) {
            var fd = frm.fields_dict[fieldname];
            if (fd) {
                fd.df.allow_on_submit = 0;
                frm.refresh_field(fieldname);
            }
        });
        _roqson_aos_fields = null;
    }

    if (_roqson_aos_grids) {
        _roqson_aos_grids.forEach(function(fieldname) {
            var fd = frm.fields_dict[fieldname];
            if (!fd || !fd.grid) return;
            fd.grid.df.allow_on_submit = 0;
            fd.grid.cannot_add_rows = true;
            fd.grid.cannot_delete_rows = true;
            if (fd.grid.wrapper) {
                fd.grid.wrapper.find('.grid-add-row, .grid-add-multiple-rows').hide();
                fd.grid.wrapper.find('.grid-remove-rows').hide();
            }
            fd.grid.refresh();
        });
        _roqson_aos_grids = null;
    }
}

function restore_locked_fields(frm) {
    if (_roqson_locked_fields) {
        _roqson_locked_fields.forEach(function(fieldname) {
            frm.set_df_property(fieldname, 'read_only', 0);
            frm.refresh_field(fieldname);
        });
        _roqson_locked_fields = null;
    }

    if (_roqson_locked_grids) {
        _roqson_locked_grids.forEach(function(fieldname) {
            var fd = frm.fields_dict[fieldname];
            if (!fd || !fd.grid) return;
            fd.grid.cannot_add_rows = false;
            fd.grid.cannot_delete_rows = false;
            fd.grid.df.read_only = 0;
            if (fd.grid.wrapper) {
                fd.grid.wrapper.find('.grid-add-row, .grid-add-multiple-rows').show();
                fd.grid.wrapper.find('.grid-remove-rows').show();
            }
            fd.grid.refresh();
        });
        _roqson_locked_grids = null;
    }

    frm.enable_save();
}

// ── Edit button ────────────────────────────────────────────────────────────

function add_edit_button(frm) {
    var btn = frm.add_custom_button(__('Edit'), function() {
        if (frm._roqson_edit_btn) {
            frm._roqson_edit_btn.remove();
            delete frm.custom_buttons[__('Edit')];
            frm._roqson_edit_btn = null;
        }
        // Reload the document from the server before entering edit mode.
        // This clears any stale child rows that exist on the client but were
        // removed from the DB by server-side workflow actions (e.g. the
        // "Order Details Table db91s8ldv2 not found" class of error).
        // The flag is read by apply_edit_mode_control on the next refresh.
        _roqson_pending_edit_after_reload = true;
        frm.reload_doc();
    });
    frm._roqson_edit_btn = btn;
    if (btn) btn.removeClass('btn-default btn-secondary').addClass('btn-warning');
}
