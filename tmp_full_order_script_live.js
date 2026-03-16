// =====================================================

// Trip Ticket (Unified) - Order-centric + Row Preview + Main-Page Features

// + Server-stamped timestamps (non-bypassable)

// Apply as ONE Client Script on DocType: "Trip Ticket"

// ERPNext 15 / Frappe 15

// =====================================================

// -------------------- Constants --------------------

const TRIP_DOCTYPE = "Trip Ticket";

const CHILD_TABLE_FIELD = "table_cpme";

const CHILD_ROW_DOCTYPE = "Trip Ticket Table";

const ORDER_LINK_FIELD = "sales_no";

const ORDER_PREVIEW_HTML_FIELD = "order_details_html";

const CHILD_PLAINTEXT_FIELD = "items_preview";

const TRIP_OUTLET_FIELD = "outlet";

const TRIP_CONTACT_FIELD = "contact_number";

const TRIP_ADDRESS_FIELD = "address";

const TRIP_CONTACT_PERSON_FIELD = "contact_person";

const TRIP_PREFERRED_DATETIME_FIELD = "preferred_datetime";       // Date field

const TRIP_PREFERRED_TIME_FIELD = "preferred_delivery_time";      // Time field

const ARRIVAL_TIME_FIELD = "arrival_time";

const COMPLETION_TIME_FIELD = "completion_time";

const TIME_IN_BUTTON_FIELD = "time_in_button";

const TIME_OUT_BUTTON_FIELD = "time_out_button";

const PROOF_FIELD = "proof_of_delivery";

const PROOF_TS_FIELD = "proof_time_stamp";

const SIGNATURE_FIELD = "customer_signature";

const SIGNATURE_TS_FIELD = "signature_timestamp";

const DELIVERY_STATUS_FIELD = "delivery_status";

const REASON_FAILURE_FIELD = "reason_for_failure";

const FAILED_STATUS_VALUE = "Failed";

const OFFENDING_HTML_FIELD = "offending_items_html";

const OFFENDING_DATA_FIELD = "offending_items_data";

const WRONG_INCOMPLETE_VALUE = "Wrong/incomplete order";

const CLAIMS_DID_NOT_ORDER_VALUE = 'Claims "did not order"';

const REQUIRE_TRIP_SAVED_BEFORE_TIME_ACTIONS = true;

const MAKE_REASON_REQUIRED_WHEN_FAILED = true;

const ORDER_DOCTYPE = "Sales";

const ORDER_OUTLET_FIELD = "customer_link";

const ORDER_ITEMS_TABLE_FIELD = "items";

const ORDER_CONTACT_CANDIDATES = ["contact_number", "contact_no", "mobile_no", "phone", "phone_no"];

const ORDER_ADDRESS_CANDIDATES = ["address", "delivery_address", "shipping_address", "address_display"];

const ORDER_CONTACT_PERSON_FIELD = "contact_person";

const ORDER_PREFERRED_DATETIME_FIELD = "preferred_delivery_date_and_time";

const PRODUCT_DOCTYPE = "Product";

const PRODUCT_NAME_FIELD_IN_ORDER_ITEMS = "items";

const PRODUCT_DESC_FIELD = "item_description";

const ORDER_ITEM_LINK_FIELD = "item";

const ALLOWED_STATUSES = ["Pending"];



const REQUIRE_TRIP_SAVED_BEFORE_SELECTING_ORDERS = false;

const PREVIEW_ITEMS_COUNT = 2;

const USE_PREVIEW_IN_CHILD_ROW_HTML = true;

const STAMP_API_METHOD = "trip_ticket_actions.stamp";

const TIME_FIELDS_TO_NORMALIZE = [

  "dispatch_time",

  ARRIVAL_TIME_FIELD,

  COMPLETION_TIME_FIELD,

  PROOF_TS_FIELD,

  SIGNATURE_TS_FIELD,

];

const DEBUG = true;



// =====================================================================

// ORDER EXCLUSIVITY � delivery_status values that "release" an order

// from its current trip ticket so it can be reassigned to a new one.

// =====================================================================

const RELEASING_DELIVERY_STATUSES = ["Failed", "Cancelled"];
const HIDDEN_WORKFLOW_ACTIONS = ["Time In", "Time Out", "Mark Delivered", "Mark Delivery Failed"];



// -------------------- Utils --------------------

function dbg(...args) {

  if (DEBUG) console.log("[TT]", ...args);

}

function warn(...args) {

  if (DEBUG) console.warn("[TT]", ...args);

}

function has_df(frm, fieldname) {
  if (!fieldname) return false;
  return !!frappe.meta.get_docfield(frm.doctype, fieldname, frm.doc.name) || 
         (frm.fields_dict && !!frm.fields_dict[fieldname]);
}

function pick_first_present(obj, candidates) {

  for (const k of candidates) {

    if (obj?.[k]) return obj[k];

  }

  return null;

}

function get_row(cdt, cdn) {

  return locals?.[cdt]?.[cdn];

}

function get_grid(frm) {

  return frm.fields_dict?.[CHILD_TABLE_FIELD]?.grid;

}

function get_grid_form(frm, cdn) {

  const grid = get_grid(frm);

  const grid_row = grid?.grid_rows_by_docname?.[cdn];

  return grid_row?.grid_form || null;

}

function set_row_html(frm, cdn, html) {

  const grid_form = get_grid_form(frm, cdn);

  const html_field = grid_form?.fields_dict?.[ORDER_PREVIEW_HTML_FIELD];

  if (html_field?.$wrapper) html_field.$wrapper.html(html);

}

function clear_row_html(frm, cdn) {

  set_row_html(frm, cdn, "");

}

function bind_row_html_actions(frm, cdn) {

  const grid_form = get_grid_form(frm, cdn);

  const html_field = grid_form?.fields_dict?.[ORDER_PREVIEW_HTML_FIELD];

  if (!html_field?.$wrapper) return;

  if (html_field.$wrapper.__tt_bound) return;

  html_field.$wrapper.__tt_bound = true;

  html_field.$wrapper.on("click", ".tt-show-more-items", async function (e) {

    e.preventDefault();

    e.stopPropagation();

    const order_name = $(this).attr("data-order");

    if (!order_name) return;

    try {

      await open_order_items_dialog(frm, order_name);

    } catch (err) {

      console.error(err);

      frappe.msgprint("Failed to open items dialog.");

    }

  });

  html_field.$wrapper.on("click", ".tt-open-order", function (e) {

    e.preventDefault();

    e.stopPropagation();

    const order_name = $(this).attr("data-order");

    if (!order_name) return;

    frappe.set_route("Form", ORDER_DOCTYPE, order_name);

  });

}

function child_field_exists(row, fieldname) {

  return row && Object.prototype.hasOwnProperty.call(row, fieldname);

}

async function set_child_value_if_exists(cdt, cdn, fieldname, value) {

  const row = get_row(cdt, cdn);

  if (!child_field_exists(row, fieldname)) return;

  await frappe.model.set_value(cdt, cdn, fieldname, value);

}

async function set_parent_value(frm, fieldname, value) {

  const df = frappe.meta.get_docfield(frm.doctype, fieldname, frm.doc.name);

  if (!df) {

    warn(`[Parent Set] docfield not found: ${fieldname}`);

    return;

  }

  await frm.set_value(fieldname, value);

  frm.refresh_field(fieldname);

  dbg(`[Parent Set] ${fieldname} =`, frm.doc?.[fieldname]);

}



// -------------------- Time-field normalization --------------------

// FIX: corrected double-escaped backslashes in regex literals

function normalize_time_value(val) {

  if (!val || typeof val !== "string") return val;

  const datetime_match = val.match(/^(\d{4}-\d{2}-\d{2})\s+(\d{1,2}:\d{2}(:\d{2})?.*)$/);

  if (datetime_match) {

    return datetime_match[1] + " " + normalize_time_value(datetime_match[2]);

  }

  const time_match = val.match(/^(\d{1,2})(:\d{2}(:\d{2})?.*)$/);

  if (time_match) {

    return time_match[1].padStart(2, "0") + time_match[2];

  }

  return val;

}

function normalize_all_time_fields(frm) {

  let fixed = 0;

  for (const fieldname of TIME_FIELDS_TO_NORMALIZE) {

    if (!has_df(frm, fieldname)) continue;

    const raw = frm.doc[fieldname];

    if (!raw) continue;

    const normalized = normalize_time_value(raw);

    if (normalized !== raw) {

      dbg(`[Time Normalize] ${fieldname}: "${raw}" ? "${normalized}"`);

      frm.doc[fieldname] = normalized;

      fixed++;

    }

  }

  if (fixed > 0) {

    for (const fieldname of TIME_FIELDS_TO_NORMALIZE) {

      if (!has_df(frm, fieldname)) continue;

      const ctrl = frm.fields_dict[fieldname];

      if (ctrl) ctrl.last_value = frm.doc[fieldname];

    }

    dbg(`[Time Normalize] Fixed ${fixed} field(s)`);

  }

}



// -------------------- Outlet lock state --------------------

function get_first_row(frm) {

  const rows = frm.doc?.[CHILD_TABLE_FIELD] || [];

  return rows.find(r => r.idx === 1) || rows[0] || null;

}

function is_outlet_locked(frm) {

  const first = get_first_row(frm);

  return !!(first && first[ORDER_LINK_FIELD]);

}



// -------------------- Parent UI visibility logic --------------------

function update_parent_visibility(frm) {

  // Ensure contact and address fields are always visible if they exist
  [TRIP_CONTACT_FIELD, TRIP_CONTACT_PERSON_FIELD, TRIP_ADDRESS_FIELD].forEach(f => {
    if (has_df(frm, f)) frm.toggle_display(f, true);
  });

  if (has_df(frm, PROOF_TS_FIELD)) {

    frm.toggle_display(PROOF_TS_FIELD, !!frm.doc?.[PROOF_FIELD] || !!frm.doc?.[PROOF_TS_FIELD]);

  }

  if (has_df(frm, SIGNATURE_TS_FIELD)) {

    frm.toggle_display(SIGNATURE_TS_FIELD, !!frm.doc?.[SIGNATURE_FIELD] || !!frm.doc?.[SIGNATURE_TS_FIELD]);

  }

  if (has_df(frm, REASON_FAILURE_FIELD) && has_df(frm, DELIVERY_STATUS_FIELD)) {

    const is_failed = frm.doc?.[DELIVERY_STATUS_FIELD] === FAILED_STATUS_VALUE;

    frm.toggle_display(REASON_FAILURE_FIELD, is_failed);

    if (MAKE_REASON_REQUIRED_WHEN_FAILED) {

      frm.set_df_property(REASON_FAILURE_FIELD, "reqd", !!is_failed);

    }

  }

  update_offending_items_visibility(frm);

}

const SAVED_ONLY_FIELDS = [

  "time_tracking",

  "customer_signature_section",

  "delivery_status",

  "proof_of_delivery",

  "customer_signature",

];

function update_saved_only_visibility(frm) {

  const is_saved = !frm.is_new() && (frm.doc?.workflow_state || "") !== "Draft";

  for (const f of SAVED_ONLY_FIELDS) {

    if (frappe.meta.get_docfield(frm.doctype, f, frm.doc.name)) {

      frm.toggle_display(f, is_saved);

    }

  }

}

function update_timestamp_visibility_saved_and_has_value(frm) {

  const is_saved = !frm.is_new();

  if (has_df(frm, PROOF_TS_FIELD)) {

    frm.toggle_display(PROOF_TS_FIELD, is_saved && (!!frm.doc?.[PROOF_FIELD] || !!frm.doc?.[PROOF_TS_FIELD]));

  }

  if (has_df(frm, SIGNATURE_TS_FIELD)) {

    frm.toggle_display(SIGNATURE_TS_FIELD, is_saved && (!!frm.doc?.[SIGNATURE_FIELD] || !!frm.doc?.[SIGNATURE_TS_FIELD]));

  }

}



// =====================================================================

// OFFENDING ITEMS

// =====================================================================

const OFFENDING_ITEMS_REASONS = [WRONG_INCOMPLETE_VALUE, CLAIMS_DID_NOT_ORDER_VALUE];

function is_offending_items_applicable(frm) {

  const is_failed = frm.doc?.[DELIVERY_STATUS_FIELD] === FAILED_STATUS_VALUE;

  const reason = frm.doc?.[REASON_FAILURE_FIELD];

  return is_failed && OFFENDING_ITEMS_REASONS.includes(reason);

}

function update_offending_items_visibility(frm) {

  const show = is_offending_items_applicable(frm);

  if (has_df(frm, OFFENDING_HTML_FIELD)) {

    frm.toggle_display(OFFENDING_HTML_FIELD, show);

  }

  if (has_df(frm, OFFENDING_DATA_FIELD)) {

    frm.toggle_display(OFFENDING_DATA_FIELD, false);

  }

  if (show) {

    render_offending_items_ui(frm);

  }

  if (!show && frm.doc?.[OFFENDING_DATA_FIELD]) {

    frm.set_value(OFFENDING_DATA_FIELD, "");

  }

}

function get_offending_data(frm) {

  const raw = frm.doc?.[OFFENDING_DATA_FIELD];

  if (!raw) return [];

  try {

    const parsed = JSON.parse(raw);

    return Array.isArray(parsed) ? parsed : [];

  } catch (e) {

    return [];

  }

}

function set_offending_data(frm, data) {

  const json = JSON.stringify(data || []);

  frm.set_value(OFFENDING_DATA_FIELD, json);

  frm.dirty();

  dbg("[Offending] Data set:", data);

}

function get_trip_order_names(frm) {

  const rows = frm.doc?.[CHILD_TABLE_FIELD] || [];

  return rows.map(r => r[ORDER_LINK_FIELD]).filter(Boolean);

}

async function render_offending_items_ui(frm) {

  const wrapper = frm.fields_dict?.[OFFENDING_HTML_FIELD]?.$wrapper;

  if (!wrapper) return;

  const order_names = get_trip_order_names(frm);

  const data = get_offending_data(frm);

  if (!order_names.length) {

    wrapper.html(`<div class="text-muted" style="padding:8px 0;">No orders in this trip ticket.</div>`);

    return;

  }

  const order_docs = {};

  const all_product_ids = [];

  for (const oname of order_names) {

    try {

      const doc = await get_order_doc_cached(frm, oname, { force_fetch: false });

      if (doc) {

        order_docs[oname] = doc;

        const items = doc[ORDER_ITEMS_TABLE_FIELD] || [];

        items.forEach(it => {

          const pid = it?.[ORDER_ITEM_LINK_FIELD];

          if (pid) all_product_ids.push(pid);

        });

      }

    } catch (e) {

      console.error(`[TT][Offending] Failed to fetch order ${oname}`, e);

    }

  }

  const desc_map = await get_products_desc_map(frm, all_product_ids);

  const order_items_map = {};

  for (const oname of order_names) {

    const doc = order_docs[oname];

    if (!doc) continue;

    const items = doc[ORDER_ITEMS_TABLE_FIELD] || [];

    order_items_map[oname] = items.map(it => {

      const pid = it?.[ORDER_ITEM_LINK_FIELD] || "";

      return { product_id: pid, product_name: desc_map[pid] || pid, qty: it.qty ?? "" };

    });

  }

  const selected_set = new Set(data.map(d => `${d.order}|||${d.product_id}`));

  let html = `<div class="tt-offending-container" style="margin:4px 0 12px 0;">`;

  html += `<label class="control-label" style="margin-bottom:8px; display:block; font-weight:600;">Offending Item/s</label>`;

  if (order_names.length === 1) {

    const oname = order_names[0];

    html += build_order_items_checkboxes(oname, order_items_map[oname] || [], selected_set);

  } else {

    for (const oname of order_names) {

      const items = order_items_map[oname] || [];

      const selected_count = items.filter(it => selected_set.has(`${oname}|||${it.product_id}`)).length;

      const badge = selected_count > 0

        ? `<span class="badge badge-danger" style="margin-left:8px; background:#e74c3c; color:#fff; border-radius:10px; padding:2px 8px; font-size:11px;">${selected_count} selected</span>`

        : "";

      html += `

        <div class="tt-offending-order" style="border:1px solid #e8e8e8; border-radius:6px; margin-bottom:8px; overflow:hidden;">

          <div class="tt-offending-order-header" data-order="${escapeHtml(oname)}"

               style="padding:10px 12px; background:#fafafa; cursor:pointer; display:flex; align-items:center; justify-content:space-between; user-select:none;">

            <div><span style="font-weight:500;">${escapeHtml(oname)}</span>${badge}</div>

            <span class="tt-offending-chevron" style="transition:transform 0.2s; font-size:12px;">&#9658;</span>

          </div>

          <div class="tt-offending-order-body" data-order="${escapeHtml(oname)}" style="display:none; padding:8px 12px;">

            ${build_order_items_checkboxes(oname, items, selected_set)}

          </div>

        </div>`;

    }

  }

  html += build_offending_summary(data, order_names.length > 1);

  html += `</div>`;

  wrapper.html(html);

  wrapper.find(".tt-offending-order-header").off("click.tt").on("click.tt", function () {

    const body = wrapper.find(`.tt-offending-order-body[data-order="${$(this).attr("data-order")}"]`);

    const chevron = $(this).find(".tt-offending-chevron");

    if (body.is(":visible")) {

      body.slideUp(150);

      chevron.css("transform", "rotate(0deg)");

    } else {

      body.slideDown(150);

      chevron.css("transform", "rotate(90deg)");

    }

  });

  wrapper.find(".tt-offending-check").off("change.tt").on("change.tt", function () {

    const order = $(this).attr("data-order");

    const product_id = $(this).attr("data-product-id");

    const product_name = $(this).attr("data-product-name");

    const checked = $(this).is(":checked");

    let current_data = get_offending_data(frm);

    if (checked) {

      const exists = current_data.some(d => d.order === order && d.product_id === product_id);

      if (!exists) current_data.push({ order, product_id, product_name });

    } else {

      current_data = current_data.filter(d => !(d.order === order && d.product_id === product_id));

    }

    set_offending_data(frm, current_data);

    render_offending_items_ui(frm);

  });

}

function build_order_items_checkboxes(order_name, items, selected_set) {

  if (!items.length) return `<div class="text-muted" style="padding:4px 0;">No items in this order.</div>`;

  let html = "";

  for (const it of items) {

    const key = `${order_name}|||${it.product_id}`;

    const is_checked = selected_set.has(key) ? "checked" : "";

    const qty_label = it.qty ? ` <span class="text-muted">(x${escapeHtml(String(it.qty))})</span>` : "";

    html += `

      <label style="display:flex; align-items:center; padding:5px 0; cursor:pointer; gap:8px; margin:0;">

        <input type="checkbox" class="tt-offending-check"

               data-order="${escapeHtml(order_name)}"

               data-product-id="${escapeHtml(it.product_id)}"

               data-product-name="${escapeHtml(it.product_name)}"

               ${is_checked}

               style="margin:0; width:15px; height:15px; flex-shrink:0;" />

        <span>${escapeHtml(it.product_name)}${qty_label}</span>

      </label>`;

  }

  return html;

}

function build_offending_summary(data, show_order_grouping) {

  if (!data.length) return "";

  let html = `<div style="margin-top:10px; padding:10px 12px; background:#fff8f8; border:1px solid #f5c6cb; border-radius:6px;">`;

  html += `<div style="font-weight:600; margin-bottom:6px; color:#721c24; font-size:12px;">Summary</div>`;

  if (show_order_grouping) {

    const grouped = {};

    for (const d of data) {

      if (!grouped[d.order]) grouped[d.order] = [];

      grouped[d.order].push(d.product_name);

    }

    for (const [order, items] of Object.entries(grouped)) {

      html += `<div style="margin-bottom:4px;"><span style="font-weight:500; font-size:12px;">${escapeHtml(order)}:</span> <span style="font-size:12px;">${items.map(i => escapeHtml(i)).join(", ")}</span></div>`;

    }

  } else {

    html += `<div style="font-size:12px;">${data.map(d => escapeHtml(d.product_name)).join(", ")}</div>`;

  }

  html += `</div>`;

  return html;

}

function render_offending_items_readonly(frm) {

  const wrapper = frm.fields_dict?.[OFFENDING_HTML_FIELD]?.$wrapper;

  if (!wrapper) return;

  const data = get_offending_data(frm);

  const order_names = get_trip_order_names(frm);

  const show_grouping = order_names.length > 1;

  if (!data.length) {

    wrapper.html(`<div class="text-muted" style="padding:8px 0;">No offending items recorded.</div>`);

    return;

  }

  wrapper.html(`

    <div style="margin:4px 0 12px 0;">

      <label class="control-label" style="margin-bottom:8px; display:block; font-weight:600;">Offending Item/s</label>

      ${build_offending_summary(data, show_grouping)}

    </div>

  `);

}



// -------------------- Data Fetch (with caching) --------------------

async function get_order_doc_cached(frm, order_name, { force_fetch = false } = {}) {

  frm.__order_cache = frm.__order_cache || {};

  if (!force_fetch && frm.__order_cache[order_name]) return frm.__order_cache[order_name];

  const r = await frappe.call({

    method: "frappe.client.get",

    args: { doctype: ORDER_DOCTYPE, name: order_name },

  });

  const sales_doc = r?.message || null;

  if (sales_doc && sales_doc.order_ref) {

    try {

      const or2 = await frappe.call({

        method: "frappe.client.get",

        args: { doctype: "Order Form", name: sales_doc.order_ref },

      });

      const order_doc = or2?.message;

      if (order_doc) {

        const supplement = [

          ...ORDER_CONTACT_CANDIDATES,

          ...ORDER_ADDRESS_CANDIDATES,

          ORDER_CONTACT_PERSON_FIELD,

          ORDER_PREFERRED_DATETIME_FIELD,

        ];

        for (const f of supplement) {

          if (sales_doc[f] == null && order_doc[f] != null) sales_doc[f] = order_doc[f];

        }

      }

    } catch (e) {

      dbg("[get_order_doc] Could not fetch Order Form for supplemental fields:", e);

    }

  }

  frm.__order_cache[order_name] = sales_doc;

  return frm.__order_cache[order_name];

}

async function get_products_desc_map(frm, product_ids) {

  frm.__product_cache = frm.__product_cache || {};

  const unique = Array.from(new Set((product_ids || []).filter(Boolean)));

  const unknown = unique.filter((p) => !frm.__product_cache[p]);

  if (!unknown.length) return frm.__product_cache;

  try {

    const rows = await frappe.db.get_list(PRODUCT_DOCTYPE, {

      filters: { name: ["in", unknown] },

      fields: ["name", PRODUCT_DESC_FIELD],

      limit_page_length: unknown.length,

    });

    (rows || []).forEach((r) => { frm.__product_cache[r.name] = r[PRODUCT_DESC_FIELD] || r.name; });

    return frm.__product_cache;

  } catch (e) {

    const rr = await frappe.call({

      method: "frappe.client.get_list",

      args: { doctype: PRODUCT_DOCTYPE, filters: { name: ["in", unknown] }, fields: ["name", PRODUCT_DESC_FIELD], limit_page_length: unknown.length },

    });

    (rr?.message || []).forEach((r) => { frm.__product_cache[r.name] = r[PRODUCT_DESC_FIELD] || r.name; });

    return frm.__product_cache;

  }

}



// -------------------- Rendering (HTML Preview) --------------------

function escapeHtml(str) {

  if (str === null || str === undefined) return "";

  return String(str)

    .replaceAll("&", "&amp;")

    .replaceAll("<", "&lt;")

    .replaceAll(">", "&gt;")

    .replaceAll('"', "&quot;")

    .replaceAll("'", "&#039;");

}

function build_html_table(lines, promos_lines) {

  const body_rows = lines.map((line) => `

    <tr>

      <td style="padding:6px 8px; border-top:1px solid #eee;">${escapeHtml(line.no)}</td>

      <td style="padding:6px 8px; border-top:1px solid #eee;">${escapeHtml(line.name)}</td>

      <td style="padding:6px 8px; border-top:1px solid #eee; text-align:right;">${escapeHtml(line.qty)}</td>

    </tr>`).join("");

  const promos_html = promos_lines.length

    ? `<div style="margin-top:10px;"><div style="font-weight:600; margin-bottom:6px;">Promos</div><div style="white-space:pre-wrap;">${escapeHtml(promos_lines.join("\n"))}</div></div>`

    : "";

  return `

    <div style="border:1px solid #eee; border-radius:8px; overflow:hidden;">

      <table style="width:100%; border-collapse:collapse;">

        <thead><tr style="background:#fafafa;">

          <th style="padding:8px; text-align:left; width:48px;">#</th>

          <th style="padding:8px; text-align:left;">Item</th>

          <th style="padding:8px; text-align:right; width:90px;">Qty</th>

        </tr></thead>

        <tbody>${body_rows}</tbody>

      </table>

    </div>${promos_html}`;

}

async function open_order_items_dialog(frm, order_name) {

  const order_doc = await get_order_doc_cached(frm, order_name, { force_fetch: false });

  if (!order_doc) { frappe.msgprint(`Order ${order_name} not found.`); return; }

  const items = order_doc?.[ORDER_ITEMS_TABLE_FIELD] || [];

  if (!items.length) { frappe.msgprint(`No items found for Order ${order_name}.`); return; }

  const product_ids = items.map((it) => it?.[ORDER_ITEM_LINK_FIELD]).filter(Boolean);

  if (order_doc.apply_promo && order_doc.reward_item) product_ids.push(order_doc.reward_item);

  const desc_map = await get_products_desc_map(frm, product_ids);

  const line_objs = items.map((it, i) => {

    const pid = it?.[ORDER_ITEM_LINK_FIELD];

    return { no: String(i + 1), name: desc_map[pid] || pid || "", qty: String(it.qty ?? "") };

  });

  const promos = [];

  if (order_doc.apply_promo) {

    const reward_id = order_doc.reward_item || "";

    const reward_name = reward_id ? (desc_map[reward_id] || reward_id) : "";

    promos.push(reward_name

      ? `� Buy ${order_doc.buy_quantity || ""} Get ${order_doc.get_quantity || ""} � Reward: ${reward_name} (Free Qty: ${order_doc.computed_free_qty || 0})`

      : `� Buy ${order_doc.buy_quantity || ""} Get ${order_doc.get_quantity || ""}`);

  }

  const html = build_html_table(line_objs, promos);

  const d = new frappe.ui.Dialog({

    title: `Items for ${order_name}`,

    size: "large",

    fields: [

      { fieldtype: "HTML", fieldname: "items_html" },

      { fieldtype: "Section Break" },

      { fieldtype: "Button", fieldname: "open_order_btn", label: "Open Order" },

    ],

    primary_action_label: "Close",

    primary_action() { d.hide(); },

  });

  d.fields_dict.items_html.$wrapper.html(html);

  d.fields_dict.open_order_btn.input.onclick = () => { d.hide(); frappe.set_route("Form", ORDER_DOCTYPE, order_name); };

  d.show();

}

function build_items_preview_text(line_objs, max_items = PREVIEW_ITEMS_COUNT) {

  if (!line_objs || !line_objs.length) return "";

  const preview = line_objs.slice(0, max_items);

  const remaining = Math.max(line_objs.length - max_items, 0);

  let text = preview.map(l => `${l.name} (x${l.qty})`).join(", ");

  if (remaining > 0) text += ` ... (+${remaining} more)`;

  return text;

}

async function populate_items_preview_for_row(frm, row, { force_fetch = false } = {}) {

  const order_name = row?.[ORDER_LINK_FIELD];

  if (!order_name) return;

  let order_doc;

  try {

    order_doc = await get_order_doc_cached(frm, order_name, { force_fetch });

  } catch (e) {

    console.error(`[TT] Failed to fetch order ${order_name}:`, e);

    return;

  }

  if (!order_doc) return;

  const items = order_doc?.[ORDER_ITEMS_TABLE_FIELD] || [];

  if (!items.length) { frappe.model.set_value(row.doctype, row.name, CHILD_PLAINTEXT_FIELD, ""); return; }

  const product_ids = items.map((it) => it?.[ORDER_ITEM_LINK_FIELD]).filter(Boolean);

  if (order_doc.apply_promo && order_doc.reward_item) product_ids.push(order_doc.reward_item);

  const desc_map = await get_products_desc_map(frm, product_ids);

  const line_objs = items.map((it, i) => {

    const pid = it?.[ORDER_ITEM_LINK_FIELD];

    return { no: String(i + 1), name: desc_map[pid] || pid || "", qty: String(it.qty ?? "") };

  });

  const preview_text = build_items_preview_text(line_objs, PREVIEW_ITEMS_COUNT);

  const current = row[CHILD_PLAINTEXT_FIELD] || "";

  if (current !== preview_text) {

    frappe.model.set_value(row.doctype, row.name, CHILD_PLAINTEXT_FIELD, preview_text);

    dbg(`[items_preview] Row ${row.idx}: "${preview_text}"`);

  }

  return { line_objs, order_doc };

}

async function populate_all_items_previews(frm) {

  const rows = frm.doc?.[CHILD_TABLE_FIELD] || [];

  const rows_with_orders = rows.filter(r => r[ORDER_LINK_FIELD]);

  if (!rows_with_orders.length) return;

  dbg(`[items_preview] Populating ${rows_with_orders.length} row(s) on refresh`);

  await Promise.all(rows_with_orders.map(row => populate_items_preview_for_row(frm, row, { force_fetch: false })));

  frm.refresh_field(CHILD_TABLE_FIELD);

}

async function render_order_details_from_doc(frm, cdt, cdn, order_doc) {

  const row = get_row(cdt, cdn);

  if (!row) return;

  const items = order_doc?.[ORDER_ITEMS_TABLE_FIELD] || [];

  if (!items.length) {

    await frappe.model.set_value(cdt, cdn, CHILD_PLAINTEXT_FIELD, "");

    set_row_html(frm, cdn, `<div class="text-muted">No items found.</div>`);

    bind_row_html_actions(frm, cdn);

    frm.refresh_field(CHILD_TABLE_FIELD);

    return;

  }

  const product_ids = items.map((it) => it?.[ORDER_ITEM_LINK_FIELD]).filter(Boolean);

  if (order_doc.apply_promo && order_doc.reward_item) product_ids.push(order_doc.reward_item);

  const desc_map = await get_products_desc_map(frm, product_ids);

  const line_objs = items.map((it, i) => {

    const pid = it?.[ORDER_ITEM_LINK_FIELD];

    return { no: String(i + 1), name: desc_map[pid] || pid || "", qty: String(it.qty ?? "") };

  });

  const promos = [];

  if (order_doc.apply_promo) {

    const reward_id = order_doc.reward_item || "";

    const reward_name = reward_id ? (desc_map[reward_id] || reward_id) : "";

    promos.push(reward_name

      ? `� Buy ${order_doc.buy_quantity || ""} Get ${order_doc.get_quantity || ""} � Reward: ${reward_name} (Free Qty: ${order_doc.computed_free_qty || 0})`

      : `� Buy ${order_doc.buy_quantity || ""} Get ${order_doc.get_quantity || ""}`);

  }

  const preview_text = build_items_preview_text(line_objs, PREVIEW_ITEMS_COUNT);

  await frappe.model.set_value(cdt, cdn, CHILD_PLAINTEXT_FIELD, preview_text);

  const order_name = row?.[ORDER_LINK_FIELD] || "";

  const full_table = build_html_table(line_objs, promos);

  const actions = `<div style="margin-top:10px; display:flex; gap:10px; align-items:center;"><a href="#" class="tt-open-order" data-order="${escapeHtml(order_name)}">Open Order</a></div>`;

  set_row_html(frm, cdn, full_table + actions);

  bind_row_html_actions(frm, cdn);

  frm.refresh_field(CHILD_TABLE_FIELD);

}



// =====================================================================

// ORDER EXCLUSIVITY CHECK

// Searches all other Trip Tickets (excluding this one) for the given

// order_name in their child table rows. Returns a conflict object if

// the order is already held by an active (non-released) trip ticket,

// or null if the order is free to assign.

// =====================================================================

async function find_conflicting_trip_ticket(frm, order_name) {

  try {

    // Query the child table doctype directly for rows with this order

    const rows = await frappe.db.get_list(CHILD_ROW_DOCTYPE, {

      filters: { [ORDER_LINK_FIELD]: order_name },

      fields: ["name", "parent"],

      limit_page_length: 50,

    });

    if (!rows || !rows.length) return null;



    // Collect unique parent trip ticket names, excluding the current document

    const other_parents = [...new Set(

      rows.map(r => r.parent).filter(p => p && p !== frm.doc.name)

    )];

    if (!other_parents.length) return null;



    // Check each parent trip ticket's delivery_status

    for (const tt_name of other_parents) {

      const tt = await frappe.db.get_value(TRIP_DOCTYPE, tt_name, [DELIVERY_STATUS_FIELD]);

      const status = tt?.[DELIVERY_STATUS_FIELD] || tt?.delivery_status || "";

      dbg(`[Exclusivity] ${tt_name} delivery_status = "${status}"`);

      // If status is NOT in the releasing list, this trip ticket is still active

      if (!RELEASING_DELIVERY_STATUSES.includes(status)) {

        return { trip_ticket: tt_name, delivery_status: status };

      }

    }

    return null;

  } catch (e) {

    console.error("[TT][Exclusivity] Error checking for conflicts:", e);

    // Fail open � don't block the user if the check itself errors out

    return null;

  }

}



// -------------------- Order Dropdown Query --------------------

// Cache taken orders per frm instance to avoid redundant server calls

async function refresh_taken_orders_cache(frm) {

  try {

    const r = await frappe.call({

      method: "get_active_trip_order_names",

      args: { current_trip: frm.doc.name || null },

    });

    frm.__taken_orders = new Set(r?.message || []);

    dbg("[set_order_query] Taken orders:", [...frm.__taken_orders]);

  } catch (e) {

    warn("[set_order_query] Failed to fetch taken orders:", e);

    frm.__taken_orders = new Set();

  }

}



function set_order_query(frm) {

  frm.set_query(ORDER_LINK_FIELD, CHILD_TABLE_FIELD, function (doc, cdt, cdn) {

    const row = get_row(cdt, cdn);

    const locked = is_outlet_locked(frm);



    if (REQUIRE_TRIP_SAVED_BEFORE_SELECTING_ORDERS && frm.is_new()) {

      return { filters: { name: ["=", "__no_results__"] } };

    }

    if (!locked && row?.idx && row.idx !== 1) {

      return { filters: { name: ["=", "__no_results__"] } };

    }



    const filters = {

      status: ["in", ALLOWED_STATUSES],

    };

    if (locked && doc[TRIP_OUTLET_FIELD]) {

      filters[ORDER_OUTLET_FIELD] = doc[TRIP_OUTLET_FIELD];

    }



    // Exclude orders already on another active trip ticket

    const taken = frm.__taken_orders ? [...frm.__taken_orders] : [];

    if (taken.length) {

      filters["name"] = ["not in", taken];

    }



    return { filters, order_by: "creation desc" };

  });

}



// -------------------- Duplicate Prevention --------------------

function is_duplicate_order(frm, current_row_name, order_name) {

  const rows = frm.doc[CHILD_TABLE_FIELD] || [];

  return rows.some((r) => r.name !== current_row_name && r[ORDER_LINK_FIELD] === order_name);

}

function clear_rows_after_first(frm) {

  const rows = frm.doc[CHILD_TABLE_FIELD] || [];

  for (const r of rows) {

    if (r.idx !== 1 && r[ORDER_LINK_FIELD]) {

      r[ORDER_LINK_FIELD] = "";

      clear_row_html(frm, r.name);

    }

  }

  frm.refresh_field(CHILD_TABLE_FIELD);

}

function keep_grid_dialog_open(frm) {

  const grid = get_grid(frm);

  if (!grid || grid.__patched_keep_open) return;

  grid.__patched_keep_open = true;

  const original_open = grid.open_grid_row;

  grid.open_grid_row = function (idx) {

    const row = grid.grid_rows[idx];

    if (row?.doc?.name) window.last_open_grid_row = row.doc.name;

    return original_open.call(this, idx);

  };

}



// -------------------- Server stamping helper --------------------

async function stamp_on_server(frm, action, extra_args = {}) {

  if (frm.is_new()) {

    frappe.msgprint("Please save the Trip Ticket first.");

    return null;

  }

  const r = await frappe.call({

    method: STAMP_API_METHOD,

    args: { trip_ticket: frm.doc.name, action: action, ...extra_args },

  });

  const msg = r?.message || null;

  if (msg?.modified) { frm.doc.modified = msg.modified; }

  return msg;

}



// -------------------- Main Order Handler --------------------

async function handle_order_selected(frm, cdt, cdn, { force_fetch = true } = {}) {

  const row = get_row(cdt, cdn);

  const selected_order = row?.[ORDER_LINK_FIELD];

  dbg("---- Order Handler ----", { selected_order, idx: row?.idx });

  if (!selected_order) {

    clear_row_html(frm, cdn);

    if (row?.idx === 1) {

      if (has_df(frm, TRIP_OUTLET_FIELD)) await set_parent_value(frm, TRIP_OUTLET_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_FIELD)) await set_parent_value(frm, TRIP_CONTACT_FIELD, "");

      if (has_df(frm, TRIP_ADDRESS_FIELD)) await set_parent_value(frm, TRIP_ADDRESS_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_PERSON_FIELD)) await set_parent_value(frm, TRIP_CONTACT_PERSON_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_DATETIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_DATETIME_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_TIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_TIME_FIELD, "");

      clear_rows_after_first(frm);

      set_order_query(frm);

    }

    return;

  }



  // ---- Intra-document duplicate check ----

  if (is_duplicate_order(frm, row.name, selected_order)) {

    frappe.msgprint(`Order ${selected_order} is already added in this Trip Ticket.`);

    await frappe.model.set_value(cdt, cdn, ORDER_LINK_FIELD, "");

    clear_row_html(frm, cdn);

    return;

  }



  // ---- Cross-document exclusivity check ----

  frappe.show_alert({ message: `Checking if ${selected_order} is available...`, indicator: "blue" }, 3);

  const conflict = await find_conflicting_trip_ticket(frm, selected_order);

  if (conflict) {

    const status_label = conflict.delivery_status

      ? ` (status: <strong>${escapeHtml(conflict.delivery_status)}</strong>)`

      : "";

    frappe.msgprint({

      title: "Order Already Assigned",

      message: `<strong>${escapeHtml(selected_order)}</strong> is already assigned to Trip Ticket

        <a href="/app/trip-ticket/${encodeURIComponent(conflict.trip_ticket)}" target="_blank">

          <strong>${escapeHtml(conflict.trip_ticket)}</strong>

        </a>${status_label}.<br><br>

        An order can only be reassigned after its current trip ticket is marked as

        <em>${RELEASING_DELIVERY_STATUSES.join("</em> or <em>")}</em>.`,

      indicator: "red",

    });

    await frappe.model.set_value(cdt, cdn, ORDER_LINK_FIELD, "");

    clear_row_html(frm, cdn);

    return;

  }



  let order_doc;

  try {

    order_doc = await get_order_doc_cached(frm, selected_order, { force_fetch });

  } catch (e) {

    console.error(e);

    frappe.msgprint(`Failed to load Order ${selected_order}.`);

    await frappe.model.set_value(cdt, cdn, ORDER_LINK_FIELD, "");

    clear_row_html(frm, cdn);

    return;

  }

  const order_outlet = order_doc?.[ORDER_OUTLET_FIELD];

  if (!order_outlet) {

    frappe.msgprint(`Order ${selected_order} has no outlet. Cannot proceed.`);

    await frappe.model.set_value(cdt, cdn, ORDER_LINK_FIELD, "");

    clear_row_html(frm, cdn);

    return;

  }

  if (row.idx === 1) {

    await set_parent_value(frm, TRIP_OUTLET_FIELD, order_outlet);

    const contact_from_order = pick_first_present(order_doc, ORDER_CONTACT_CANDIDATES) || "";

    const address_from_order = pick_first_present(order_doc, ORDER_ADDRESS_CANDIDATES) || "";

    const contact_person_from_order = (order_doc?.[ORDER_CONTACT_PERSON_FIELD] || "") + "";

    // Split the order's preferred_delivery_date_and_time into separate date and time

    const preferred_datetime_raw = order_doc?.[ORDER_PREFERRED_DATETIME_FIELD] || "";

    const preferred_date_from_order = preferred_datetime_raw ? preferred_datetime_raw.split(" ")[0] : "";

    const preferred_time_from_order = (preferred_datetime_raw && preferred_datetime_raw.includes(" ")) ? preferred_datetime_raw.split(" ")[1] : "";

    await set_parent_value(frm, TRIP_CONTACT_FIELD, contact_from_order);

    await set_parent_value(frm, TRIP_ADDRESS_FIELD, address_from_order);

    if (has_df(frm, TRIP_CONTACT_PERSON_FIELD)) {

      await set_parent_value(frm, TRIP_CONTACT_PERSON_FIELD, contact_person_from_order);

    }

    if (has_df(frm, TRIP_PREFERRED_DATETIME_FIELD)) {

      await set_parent_value(frm, TRIP_PREFERRED_DATETIME_FIELD, preferred_date_from_order);

    }

    if (has_df(frm, TRIP_PREFERRED_TIME_FIELD)) {

      await set_parent_value(frm, TRIP_PREFERRED_TIME_FIELD, preferred_time_from_order);

    }

    clear_rows_after_first(frm);

    set_order_query(frm);

  } else {

    const locked_outlet = frm.doc?.[TRIP_OUTLET_FIELD];

    if (locked_outlet && order_outlet !== locked_outlet) {

      frappe.msgprint(`Only orders from outlet "${locked_outlet}" are allowed.`);

      await frappe.model.set_value(cdt, cdn, ORDER_LINK_FIELD, "");

      clear_row_html(frm, cdn);

      return;

    }

  }

  await render_order_details_from_doc(frm, cdt, cdn, order_doc);

}



// -------------------- Main Trip Ticket Page Actions --------------------

async function handle_time_in(frm) {

  if (REQUIRE_TRIP_SAVED_BEFORE_TIME_ACTIONS && frm.is_new()) {

    frappe.msgprint("Please save the Trip Ticket before recording Time In.");

    return;

  }

  const res = await stamp_on_server(frm, "time_in");

  if (!res) return;

  if (res.field && res.value != null) { await set_parent_value(frm, res.field, res.value); }

  frappe.show_alert({ message: "Time In recorded", indicator: "green" }, 3);

}

async function handle_time_out(frm) {

  if (REQUIRE_TRIP_SAVED_BEFORE_TIME_ACTIONS && frm.is_new()) {

    frappe.msgprint("Please save the Trip Ticket before recording Time Out.");

    return;

  }

  const res = await stamp_on_server(frm, "time_out");

  if (!res) return;

  if (res.field && res.value != null) { await set_parent_value(frm, res.field, res.value); }

  frappe.show_alert({ message: "Time Out recorded", indicator: "green" }, 3);

}

function wait_ms(ms) {

  return new Promise((resolve) => setTimeout(resolve, ms));

}

function get_field_value_best_effort(frm, fieldname) {

  try {

    const f = frm.get_field(fieldname);

    if (f && typeof f.get_value === "function") return f.get_value();

    if (f && "value" in f) return f.value;

  } catch (e) {}

  return frm.doc?.[fieldname];

}

async function handle_proof_changed(frm) {

  if (frm.is_new()) {

    update_parent_visibility(frm);

    update_saved_only_visibility(frm);

    update_timestamp_visibility_saved_and_has_value(frm);

    return;

  }

  await wait_ms(200);

  const val = get_field_value_best_effort(frm, PROOF_FIELD);

  const has_media = !!val;

  const res = await stamp_on_server(frm, "proof", { media_present: has_media });

  if (res && res.field) { await set_parent_value(frm, res.field, res.value ?? ""); }

  update_parent_visibility(frm);

  update_timestamp_visibility_saved_and_has_value(frm);

}

async function handle_signature_changed(frm) {

  if (frm.is_new()) {

    update_parent_visibility(frm);

    update_saved_only_visibility(frm);

    update_timestamp_visibility_saved_and_has_value(frm);

    return;

  }

  await wait_ms(200);

  const val = get_field_value_best_effort(frm, SIGNATURE_FIELD);

  const has_media = !!val;

  const res = await stamp_on_server(frm, "signature", { media_present: has_media });

  if (res && res.field) { await set_parent_value(frm, res.field, res.value ?? ""); }

  update_parent_visibility(frm);

  update_timestamp_visibility_saved_and_has_value(frm);

}

function handle_delivery_status_changed(frm) {

  update_parent_visibility(frm);

}

function clear_default_delivery_status_on_new(frm) {

  if (!frm.is_new()) return;

  if ((frm.doc?.[DELIVERY_STATUS_FIELD] || "") === "Successful") {

    frm.set_value(DELIVERY_STATUS_FIELD, "");

  }

}

function hide_redundant_workflow_actions(frm) {

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

}



// -------------------- Contact Person Auto-fill --------------------

async function autofill_contact_person_from_outlet(frm) {

  const outlet = frm.doc[TRIP_OUTLET_FIELD];

  if (!outlet) return;

  try {

    const r = await frappe.call({

      method: "frappe.client.get",

      args: { doctype: "Customer Information", name: outlet },

    });

    const contact = r?.message?.[ORDER_CONTACT_PERSON_FIELD] || r?.message?.contact_person || "";

    if (contact) {

      await set_parent_value(frm, TRIP_CONTACT_PERSON_FIELD, contact);

      frappe.show_alert({ message: "Contact person auto-filled from outlet.", indicator: "blue" }, 3);

    }

  } catch (e) {

    dbg("[Contact Person] Failed to fetch outlet doc:", e);

  }

}



// -------------------- Events --------------------

frappe.ui.form.on(TRIP_DOCTYPE, {

  setup(frm) {

    set_order_query(frm);

  },

  async refresh(frm) {

    normalize_all_time_fields(frm);

    clear_default_delivery_status_on_new(frm);

    if (frm.is_new() && !frm.doc[TRIP_PREFERRED_DATETIME_FIELD]) {

      frm.set_value(TRIP_PREFERRED_DATETIME_FIELD, frappe.datetime.get_today());

    }

    await refresh_taken_orders_cache(frm);

    set_order_query(frm);

    keep_grid_dialog_open(frm);

    hide_redundant_workflow_actions(frm);

    update_parent_visibility(frm);

    update_saved_only_visibility(frm);

    update_timestamp_visibility_saved_and_has_value(frm);

    await populate_all_items_previews(frm);

    if (is_offending_items_applicable(frm)) {

      render_offending_items_ui(frm);

    }

  },

  async after_save(frm) {

    normalize_all_time_fields(frm);

    await refresh_taken_orders_cache(frm);

    hide_redundant_workflow_actions(frm);

    update_parent_visibility(frm);

    update_saved_only_visibility(frm);

    update_timestamp_visibility_saved_and_has_value(frm);

    set_order_query(frm);

  },

  async [TIME_IN_BUTTON_FIELD](frm) {

    await handle_time_in(frm);

  },

  async [TIME_OUT_BUTTON_FIELD](frm) {

    await handle_time_out(frm);

  },

  async [PROOF_FIELD](frm) {

    await handle_proof_changed(frm);

  },

  async [SIGNATURE_FIELD](frm) {

    await handle_signature_changed(frm);

  },

  [DELIVERY_STATUS_FIELD](frm) {

    handle_delivery_status_changed(frm);

  },

  [REASON_FAILURE_FIELD](frm) {

    update_offending_items_visibility(frm);

  },

  async [TRIP_CONTACT_PERSON_FIELD](frm) {

    if (!frm.doc[TRIP_CONTACT_PERSON_FIELD] && frm.doc[TRIP_OUTLET_FIELD]) {

      frappe.show_alert({ message: "Contact person is empty � refilling from outlet...", indicator: "orange" }, 3);

      await autofill_contact_person_from_outlet(frm);

    }

  },

});

frappe.ui.form.on(CHILD_ROW_DOCTYPE, {

  async [ORDER_LINK_FIELD](frm, cdt, cdn) {

    await handle_order_selected(frm, cdt, cdn, { force_fetch: true });

  },

  async form_render(frm, cdt, cdn) {

    const row = get_row(cdt, cdn);

    if (!row?.[ORDER_LINK_FIELD]) return;

    const order_doc = await get_order_doc_cached(frm, row[ORDER_LINK_FIELD], { force_fetch: false });

    if (order_doc) await render_order_details_from_doc(frm, cdt, cdn, order_doc);

  },

  async [`${CHILD_TABLE_FIELD}_remove`](frm) {

    const rows = frm.doc?.[CHILD_TABLE_FIELD] || [];

    if (rows.length === 0) {

      if (has_df(frm, TRIP_OUTLET_FIELD)) await set_parent_value(frm, TRIP_OUTLET_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_FIELD)) await set_parent_value(frm, TRIP_CONTACT_FIELD, "");

      if (has_df(frm, TRIP_ADDRESS_FIELD)) await set_parent_value(frm, TRIP_ADDRESS_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_PERSON_FIELD)) await set_parent_value(frm, TRIP_CONTACT_PERSON_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_DATETIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_DATETIME_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_TIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_TIME_FIELD, "");

      set_order_query(frm);

    }

  },

  async [`${CHILD_TABLE_FIELD}_delete`](frm) {

    const rows = frm.doc?.[CHILD_TABLE_FIELD] || [];

    if (rows.length === 0) {

      if (has_df(frm, TRIP_OUTLET_FIELD)) await set_parent_value(frm, TRIP_OUTLET_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_FIELD)) await set_parent_value(frm, TRIP_CONTACT_FIELD, "");

      if (has_df(frm, TRIP_ADDRESS_FIELD)) await set_parent_value(frm, TRIP_ADDRESS_FIELD, "");

      if (has_df(frm, TRIP_CONTACT_PERSON_FIELD)) await set_parent_value(frm, TRIP_CONTACT_PERSON_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_DATETIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_DATETIME_FIELD, "");

      if (has_df(frm, TRIP_PREFERRED_TIME_FIELD)) await set_parent_value(frm, TRIP_PREFERRED_TIME_FIELD, "");

      set_order_query(frm);

    }

  },

});


