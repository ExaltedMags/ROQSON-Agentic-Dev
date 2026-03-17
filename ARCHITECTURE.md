# roqson_core App Architecture

**Generated**: 2026-03-17 via live discovery pass
**Source**: Full fetch of every active script from roqson-industrial-sales.s.frappe.cloud

---

## Discovery Summary

| Category | Active | Total (including disabled) |
|---|---|---|
| Server Scripts — DocType Event | 49 | 70 |
| Server Scripts — API | 26 | 35 |
| Server Scripts — Permission Query | 13 | 14 |
| Server Scripts — Scheduler Event | 2 | 7 |
| **Server Scripts total** | **90** | **127** |
| Client Scripts | 122 | 176 |

The counts differ from the earlier FEASIBILITY_ANALYSIS.md estimates (which used ~43 DocType Events, ~28 APIs). The live figures are authoritative.

---

## Full Directory Tree

```
roqson_core/
├── setup.py
├── MANIFEST.in
├── requirements.txt
└── roqson_core/
    ├── __init__.py
    ├── hooks.py                    ← app metadata; doc_events, permission_query_conditions,
    │                                 scheduler_events, fixtures (all wired here)
    ├── modules.txt
    ├── patches.txt                 ← data migration patches (Phase 8 if needed)
    │
    ├── api.py                      ← 26 API Server Scripts → @frappe.whitelist() functions
    ├── tasks.py                    ← 2 Scheduler Event scripts
    ├── permissions.py              ← 13 Permission Query scripts
    │                                 + 2 misclassified DocType Events (Archive CI,
    │                                   Archive Sales Personnel — see note below)
    │
    ├── order_form.py               ← 20 Order Form DocType Event scripts
    ├── trips.py                    ← 8 Trips DocType Event scripts
    ├── credit_application.py       ← 6 Credit Application DocType Event scripts
    ├── customer_information.py     ← 3 Customer Information DocType Event scripts
    ├── sales.py                    ← 2 Sales DocType Event scripts
    ├── receipt.py                  ← 2 Receipt DocType Event scripts
    ├── price_change_request.py     ← 1 Price Change Request DocType Event script
    ├── cost_tier.py                ← 1 Cost Tier DocType Event script
    ├── inventory_entry.py          ← 1 Inventory Entry DocType Event script
    │                                 (Inventory Stock In — After Insert)
    ├── inventory_ledger.py         ← 3 Inventory Ledger DocType Event scripts
    │                                 (Source, Inventory Notifications, Inventory Entry Quantity)
    │
    ├── fixtures/
    │   ├── .gitkeep
    │   ├── custom_field.json       ← Phase 4: 44 custom fields
    │   ├── print_format.json       ← Phase 4: 2 print formats
    │   ├── doctype_order_form.json ← Phase 8: 1 of 59 DocType fixtures
    │   ├── doctype_trips.json      ← Phase 8
    │   ├── doctype_sales.json      ← Phase 8
    │   ├── ... (one file per DocType group)
    │   ├── workflow_order_workflow.json               ← Phase 9
    │   ├── workflow_time_in_time_out.json             ← Phase 9
    │   ├── workflow_credit_approval.json              ← Phase 9
    │   └── workflow_credit_application_request.json  ← Phase 9
    │
    └── public/                     ← FUTURE PHASE (not in Phases 0–10)
        ├── css/
        │   └── roqson_core.css     ← future: CSS extracted from 29 CSS-injecting CS
        └── js/
            ├── order_form.bundle.js   ← future: 33 Order Form Client Scripts
            ├── trips.bundle.js        ← future: 10 Trips Client Scripts
            └── ...
```

---

## Script → File Mapping

### api.py — 26 functions

All are `@frappe.whitelist()`. New endpoint path: `roqson_core.api.<function_name>`

| Server Script (live name) | Python function name | Called by Client Script | Notes |
|---|---|---|---|
| Get Product Stock API | `get_product_stock` | Order Form: Stock Availability UX | Core; multi-mode stock query |
| CSF Get Last Order | `get_last_outlet_order` | CSF: Get Last Order | Survey form helper |
| CSF: Add Photos | `get_survey_photos` | CSF: Add photos | Survey photo gallery |
| Get Promo Warehouse | `get_promo_warehouse` | Order Form Promos | Promo reward logic |
| Eligible Orders by Outlet | `get_eligible_orders` | Full Order Script | Trips creation filter |
| Timestamping | `stamp` | Full Order Script | Server-side time injection for Trips |
| Get Active Trip Order Names | `get_active_trip_order_names` | Full Order Script | Prevents duplicate trip entries |
| get_receipt_history_for_sale | `get_receipt_history_for_sale` | Sales: Receipts Section | Receipt panel on Sales form |
| get_receivable_sales_for_customer | `get_receivable_sales_for_customer` | Receipt: Form Controller (set_query — verify) | Filters Sales link in Receipt grid |
| get_customer_orders | `get_customer_orders` | Order History Summary | Customer order history panel |
| Product: Get Inventory | `get_product_inventory` | Product: Show Inventory | Per-warehouse inventory display |
| RPM Get Fields | `rpm_get_doctype_fields` | RPM admin page | Role Permission Manager |
| RPM Get Field Permissions | `rpm_get_field_permissions` | RPM admin page | Role Permission Manager |
| RPM Get Permissions | `rpm_get_role_permissions` | RPM admin page | Role Permission Manager |
| RPM Get Roles | `rpm_get_all_roles` | RPM admin page | Role Permission Manager |
| RPM Get Doctypes | `rpm_get_all_doctypes` | RPM admin page | Role Permission Manager |
| RPM Update Permission | `rpm_update_permission` | RPM admin page | Role Permission Manager |
| RPM Update Field Permlevel | `rpm_update_field_permlevel` | RPM admin page | Role Permission Manager |
| RPM Bulk Update Fields | `rpm_bulk_update_field_permlevels` | RPM admin page | Role Permission Manager |
| Fix Preferred Datetime Field v2 | `fix_preferred_datetime_v2` | none (one-time utility) | Data fix; keep disabled after migration |
| Fix Credit App | `fix_credit_application_table` | none (one-time utility) | Schema inspect utility |
| fix_order_titles_utility | `fix_order_titles_utility` | none (one-time utility) | Display name backfill |
| temp_enable_order_form_comments | `temp_enable_order_form_comments` | none (one-time utility) | Debug toggle; disable after migration |
| test_hello | `test_hello` | none (test stub) | Keep disabled; do not delete |
| trip_ticket_workflow_updater | `trip_ticket_workflow_updater` | none (one-time utility) | Workflow state setup; keep disabled |
| Trip Ticket Workflow Updater (API) | `trip_ticket_workflow_updater_v2` | none (one-time utility) | Duplicate; keep disabled |

**Client Scripts requiring endpoint path update in Phase 3** (9 scripts, 10 API calls):

| Client Script | Old `frappe.handler.run_server_script` call | New `roqson_core.api.*` path |
|---|---|---|
| Order Form: Stock Availability UX | `Get Product Stock API` | `get_product_stock` |
| CSF: Get Last Order | `CSF Get Last Order` | `get_last_outlet_order` |
| CSF: Add photos | `CSF: Add Photos` | `get_survey_photos` |
| Order Form Promos | `Get Promo Warehouse` | `get_promo_warehouse` |
| Full Order Script | `Get Active Trip Order Names` | `get_active_trip_order_names` |
| Full Order Script | `Timestamping` | `stamp` |
| Sales: Receipts Section | `get_receipt_history_for_sale` | `get_receipt_history_for_sale` |
| Order History Summary | `get_customer_orders` | `get_customer_orders` |
| Product: Show Inventory | `Product: Get Inventory` | `get_product_inventory` |

---

### order_form.py — 20 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| Auto-close PCRs on Order Delete | Before Delete | `before_delete` |
| MOP Cash Terms Bypass | Before Save | `before_save` (merged) |
| Auto-fill Approved By | Before Save | `before_save` (merged) |
| Validate Term Request Change | Before Save | `before_save` (merged) |
| Allow Delivery Address Edit for Admin | Before Save | `before_save` (merged) |
| Price Edit | Before Save | `before_save` (merged) |
| Price Modified Flag | Before Save | `before_save` (merged) |
| Notes Acknowledgment Validation | Before Save | `before_save` (merged) |
| Order Form Admin Edit Bypass | Before Save | `before_save` (merged) |
| Reservation cannot exceed available | Before Submit | `before_submit` |
| Auto Approve | After Save | `after_save` |
| Price Change Request Creator | After Save | `after_save` (merged) |
| Auto Create Sales on Approval | After Save (Submitted Document) | `on_update_after_submit` |
| Approved, Rejected, Reserved… | After Save (Submitted Document) | `on_update_after_submit` (merged) |
| Auto Cancel Sales on Order Cancellation | After Save (Submitted Document) | `on_update_after_submit` (merged) |
| Inventory Stock Out | After Save (Submitted Document) | `on_update_after_submit` (merged) |
| Order Form Stock Notiffication | After Submit | `on_submit` |
| Order Submitted Notification | After Submit | `on_submit` (merged) |
| Order Canceled Notification | After Cancel | `on_cancel` |
| Inventory Stock Canceled | After Cancel | `on_cancel` (merged) |

> **Note**: Multiple scripts on the same event are merged into one function in order_form.py. The calling sequence must be preserved exactly. Read each script carefully before combining.

---

### trips.py — 8 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| Trip Numbering | Before Insert | `before_insert` |
| Fix Dispatch Time | Before Validate | `before_validate` |
| Enforce Eligibility | Before Save | `before_save` |
| Trip Ticket Multi-Driver Sync | Before Save | `before_save` (merged) |
| Trip Ticket Transit Update | Before Save | `before_save` (merged) |
| Delivery Status Notification | Before Save | `before_save` (merged) |
| Trip Ticket Creation Notification | After Insert | `after_insert` |
| Trip Ticket and Order Form Traceability | After Save | `after_save` |

---

### credit_application.py — 6 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| CA: Enforce Signatures | Before Save | `before_save` |
| CA: Supporting Documents | Before Submit | `before_submit` |
| CA: Minimum | Before Submit | `before_submit` (merged) |
| CA: Update Credit Approval | After Save | `after_save` |
| CA: Needs Review Notificaton | After Save (Submitted Document) | `on_update_after_submit` |
| CA: For Completion Notif | After Save (Submitted Document) | `on_update_after_submit` (merged) |

---

### customer_information.py — 3 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| CI: Unlimited Credit Set | Before Save | `before_save` |
| Customer Information: Fields Validation | Before Save | `before_save` (merged) |
| CI: Allow Edit After Subm | Before Save (Submitted Document) | `on_update_after_submit` |

> **Archive CI** (currently classified as DocType Event) contains permission query logic and is migrated to **permissions.py** instead. See the misclassification note below.

---

### sales.py — 2 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| Auto Cancel Order on Sales Cancellation | Before Save | `before_save` |
| Sales Inventory Stock Out | After Save | `after_save` |

---

### receipt.py — 2 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| Receipt: Revert Sales on Cancel | Before Cancel | `before_cancel` |
| Receipt: Update Sales on Submit | After Submit | `on_submit` |

---

### price_change_request.py — 1 function

| Server Script (live name) | Event | Python function |
|---|---|---|
| Process PCR Approval | After Save | `after_save` |

---

### cost_tier.py — 1 function

| Server Script (live name) | Event | Python function |
|---|---|---|
| Cost Tier: Display Name | Before Save | `before_save` |

---

### inventory_entry.py — 1 function

| Server Script (live name) | Event | Python function |
|---|---|---|
| Inventory Stock In | After Insert | `after_insert` |

---

### inventory_ledger.py — 3 functions

| Server Script (live name) | Event | Python function |
|---|---|---|
| Source | Before Insert | `before_insert` |
| Inventory Notifications | After Insert | `after_insert` |
| Inventory Entry Quantity | After Save (Submitted Document) | `on_update_after_submit` |

> **Resolved**: "Inventory Entry Quantity" had no `reference_doctype` set in the live instance but its body uses `doc.product`, `doc.warehouse`, `doc.quantity` — Inventory Ledger fields. Confirmed it belongs in `inventory_ledger.py`. The `reference_doctype` should be set to `Inventory Ledger` in the live instance before Phase 5.

---

### permissions.py — 15 conditions

| Server Script (live name) | DocType | Python function | Original type |
|---|---|---|---|
| Archive Order Form | Order Form | `get_order_form_conditions` | Permission Query |
| Archive Trip Ticket | Trips | `get_trips_conditions` | Permission Query |
| Sales Permission Query | Sales | `get_sales_conditions` | Permission Query |
| Archive Credit Application | Credit Application | `get_credit_application_conditions` | Permission Query |
| Archive CSV | Customer Survey Form | `get_customer_survey_form_conditions` | Permission Query |
| Archive Product | Product | `get_product_conditions` | Permission Query |
| Archive NOB | Nature of Business | `get_nature_of_business_conditions` | Permission Query |
| Archive Promos | Promos | `get_promos_conditions` | Permission Query |
| Archive Discounts | Discounts | `get_discounts_conditions` | Permission Query |
| Archive Teritorries | Territories | `get_territories_conditions` | Permission Query |
| Archive Vehicle | Vehicles | `get_vehicles_conditions` | Permission Query |
| Archive Warehouses | Warehouses | `get_warehouses_conditions` | Permission Query |
| Archive Brands | Brands | `get_brands_conditions` | Permission Query |
| Archive CI | Customer Information | `get_customer_information_conditions` | **DocType Event (misclassified)** |
| Archive Sales Personnel | Sales Personnel | `get_sales_personnel_conditions` | **DocType Event (misclassified)** |

**Naming convention**: `get_<doctype_snake_case>_conditions(user=None) -> str`

**Misclassification note**: "Archive CI" and "Archive Sales Personnel" are stored as DocType Event scripts but contain permission query logic (they set a `conditions` variable and check `frappe.form_dict.get("cmd")`). They do **not** fire as real DocType Events in production — they should be migrated as permission conditions, not doc event handlers. Verify this by checking if any Order Form or Customer Information saves throw errors after disabling them post-migration.

---

### tasks.py — 2 functions

| Server Script (live name) | Frequency | Python function |
|---|---|---|
| Auto Archive Expired Promos | Daily | `auto_archive_expired_promos` |
| Overheld Reservation Notification | Hourly | `notify_overheld_reservations` |

`hooks.py` scheduler_events:
```python
scheduler_events = {
    "daily": ["roqson_core.tasks.auto_archive_expired_promos"],
    "hourly": ["roqson_core.tasks.notify_overheld_reservations"],
}
```

---

## Client Scripts — What Stays and Why

All **122 enabled** Client Scripts remain in the Frappe UI as Client Scripts for the duration of Phases 0–10. They are **not** migrated to app JS bundles.

**Reason 1 — Scope**: JS bundle migration requires a webpack pipeline in the app. That is a separate project with its own testing surface. The current migration goal is to get Server Scripts and fixtures into version control.

**Reason 2 — Safety**: Client Scripts live in the database and can be patched via API without a bench redeploy. If a CS has a bug post-migration, `roqson.safe_update_script()` fixes it in seconds. An app JS bundle requires a git commit and bench deploy.

**Reason 3 — Risk profile**: The 9 Client Scripts that call Server Script APIs are the only ones that break during migration (Phase 3). Their new endpoint paths are known. All other Client Scripts are unaffected.

### Client Script breakdown by DocType

| DocType | Enabled CS | Category summary |
|---|---|---|
| Order Form | 33 | 12 css_injection, 28 ui_behaviour, 8 business_logic |
| Credit Application | 13 | 0 css_injection, 13 ui_behaviour, 2 business_logic |
| Customer Information | 10 | 2 css_injection, 10 ui_behaviour, 2 business_logic |
| Trips | 10 | 3 css_injection, 10 ui_behaviour, 3 business_logic |
| Customer Survey Form | 9 | 3 css_injection, 9 ui_behaviour, 2 business_logic |
| Sales | 7 | 4 css_injection, 7 ui_behaviour, 3 business_logic |
| Inventory Ledger | 7 | 2 css_injection, 7 ui_behaviour, 0 business_logic |
| Discounts | 5 | 0 css_injection, 5 ui_behaviour, 0 business_logic |
| Product | 3 | 0 css_injection, 2 ui_behaviour, 1 business_logic |
| Customer Information (archive) | 3 | 1 css_injection, 3 ui_behaviour, 1 business_logic |
| Others (PH Address, Address, Vehicles, Brands, etc.) | 22 | mostly archive/ui_behaviour |

---

## CSS Injection Audit

**29 Client Scripts** inject CSS into the page via `<style>` tags or jQuery `.css()` calls. This is functional but inflates the per-page DOM.

In a future cleanup phase (outside Phases 0–10), all CSS injection should be extracted to `public/css/roqson_core.css` and loaded via `app_include_css` in hooks.py.

### Scripts with CSS injection

| Client Script | DocType | Injection type |
|---|---|---|
| Sales: Form Logic & Calculations | Sales | style tag + DOM |
| Order Form: Footer Row Summary Tab | Order Form | style tag |
| Order Form: Totals Footer Row | Order Form | style tag |
| Order Form: Table Management & Calculation | Order Form | style tag |
| Sales List Script | Sales | style tag |
| Sales Pick-up Confirmation | Sales | style tag |
| Order Form: Stock Availability UX | Order Form | style tag |
| DSP Mandatory | Order Form | style tag |
| Price Modified Flag | Order Form | style tag |
| Price Change Request Pop Up | Notification Log | style tag |
| Workspace: PCR Popup | Workspace | style tag |
| CSF: Get Last Order | Customer Survey Form | style tag |
| CSF: Add photos | Customer Survey Form | style tag |
| Full Order Script | Trips | style tag |
| Trip Ticket: Multi-Driver Operations | Trips | style tag |
| Order Form Display | Order Form | style tag |
| Archive Trip Ticket List | Trips | style tag |
| Order Form Promos | Order Form | style tag |
| Sales: Receipts Section | Sales | style tag |
| Sales: Paid Validation | Sales | style tag |
| Order Form List - Master | Order Form | style tag |
| Order Form UX Fix | Order Form | style tag |
| Order Form: Edit Mode Control | Order Form | style tag |
| Notes Acknowledgment | Order Form | style tag |
| Archive CI List | Customer Information | style tag |
| Movement Type Accessibility | Inventory Ledger | style tag |
| Inventory Ledger Audit Trail | Inventory Ledger | style tag |
| Notes Indicator CSF | Customer Survey Form | style tag |
| Order History Summary | Customer Information | style tag |

---

## hooks.py Skeleton (target state after Phases 3–7)

```python
app_name = "roqson_core"
app_title = "Roqson Core"
app_publisher = "ROQSON"
app_description = "ROQSON Industrial Sales core customizations"
app_version = "0.0.1"
app_license = "MIT"

fixtures = [
    {
        "dt": "Custom Field",
        "filters": [["dt", "in", [
            "Trips", "Address", "Vehicle", "Vehicles", "Driver",
            "Print Settings", "Order Form", "Sales", "Promos", "Contact"
        ]]]
    },
    {
        "dt": "Print Format",
        "filters": [["name", "in", ["Sales Billing Statement", "Billing Statement"]]]
    },
    # Phase 8: DocType fixtures added here
    # Phase 9: Workflow fixtures added here
]

doc_events = {
    "Order Form": {
        "before_delete":           "roqson_core.order_form.before_delete",
        "before_save":             "roqson_core.order_form.before_save",
        "before_submit":           "roqson_core.order_form.before_submit",
        "after_save":              "roqson_core.order_form.after_save",
        "on_update_after_submit":  "roqson_core.order_form.on_update_after_submit",
        "on_submit":               "roqson_core.order_form.on_submit",
        "on_cancel":               "roqson_core.order_form.on_cancel",
    },
    "Trips": {
        "before_insert":           "roqson_core.trips.before_insert",
        "before_validate":         "roqson_core.trips.before_validate",
        "before_save":             "roqson_core.trips.before_save",
        "after_insert":            "roqson_core.trips.after_insert",
        "after_save":              "roqson_core.trips.after_save",
    },
    "Credit Application": {
        "before_save":             "roqson_core.credit_application.before_save",
        "before_submit":           "roqson_core.credit_application.before_submit",
        "after_save":              "roqson_core.credit_application.after_save",
        "on_update_after_submit":  "roqson_core.credit_application.on_update_after_submit",
    },
    "Customer Information": {
        "before_save":             "roqson_core.customer_information.before_save",
        "on_update_after_submit":  "roqson_core.customer_information.on_update_after_submit",
    },
    "Sales": {
        "before_save":             "roqson_core.sales.before_save",
        "after_save":              "roqson_core.sales.after_save",
    },
    "Receipt": {
        "before_cancel":           "roqson_core.receipt.before_cancel",
        "on_submit":               "roqson_core.receipt.on_submit",
    },
    "Price Change Request": {
        "after_save":              "roqson_core.price_change_request.after_save",
    },
    "Cost Tier": {
        "before_save":             "roqson_core.cost_tier.before_save",
    },
    "Inventory Entry": {
        "after_insert":            "roqson_core.inventory_entry.after_insert",
    },
    "Inventory Ledger": {
        "before_insert":           "roqson_core.inventory_ledger.before_insert",
        "after_insert":            "roqson_core.inventory_ledger.after_insert",
        "on_update_after_submit":  "roqson_core.inventory_ledger.on_update_after_submit",
    },
}

permission_query_conditions = {
    "Order Form":           "roqson_core.permissions.get_order_form_conditions",
    "Trips":                "roqson_core.permissions.get_trips_conditions",
    "Sales":                "roqson_core.permissions.get_sales_conditions",
    "Credit Application":   "roqson_core.permissions.get_credit_application_conditions",
    "Customer Survey Form": "roqson_core.permissions.get_customer_survey_form_conditions",
    "Customer Information": "roqson_core.permissions.get_customer_information_conditions",
    "Product":              "roqson_core.permissions.get_product_conditions",
    "Nature of Business":   "roqson_core.permissions.get_nature_of_business_conditions",
    "Promos":               "roqson_core.permissions.get_promos_conditions",
    "Discounts":            "roqson_core.permissions.get_discounts_conditions",
    "Territories":          "roqson_core.permissions.get_territories_conditions",
    "Vehicles":             "roqson_core.permissions.get_vehicles_conditions",
    "Warehouses":           "roqson_core.permissions.get_warehouses_conditions",
    "Brands":               "roqson_core.permissions.get_brands_conditions",
    "Sales Personnel":      "roqson_core.permissions.get_sales_personnel_conditions",
}

scheduler_events = {
    "daily":  ["roqson_core.tasks.auto_archive_expired_promos"],
    "hourly": ["roqson_core.tasks.notify_overheld_reservations"],
}
```

> **Import path**: Verify on staging before wiring any hooks. Run the path test from Phase 5.0 of the PRD. If `roqson_core.order_form` resolves, use that form. If only `roqson_core.roqson_core.order_form` resolves, prefix all paths accordingly.

---

## Special Cases and Risks

### 1. Misclassified Permission Queries (2 scripts)
"Archive CI" and "Archive Sales Personnel" are DocType Event scripts whose bodies implement permission query logic. They will be ported to `permissions.py` rather than their respective DocType modules. After migration, test that:
- Customer Information list view does not show archived records
- Sales Personnel link fields do not offer archived records

### 2. Orphaned Inventory Entry Quantity (1 script)
"Inventory Entry Quantity" has no `reference_doctype`. Before migrating, run:
```python
import roqson
doc = roqson.get_doc("Server Script", "Inventory Entry Quantity")
print(doc.get("reference_doctype"))
print(doc.get("doctype_event"))
print(doc.get("script"))
```
Assign to `inventory_entry.py` if confirmed to target Inventory Entry; otherwise investigate.

### 3. One-time Utility Scripts in api.py (6 scripts)
These were written for one-time fixes and are no longer called by any Client Script:
- `fix_preferred_datetime_v2`
- `fix_credit_application_table` (Fix Credit App)
- `fix_order_titles_utility`
- `temp_enable_order_form_comments`
- `test_hello`
- `trip_ticket_workflow_updater` / `trip_ticket_workflow_updater_v2`

Port them to `api.py` to satisfy the disable-original rule, but mark them with a `# UTILITY — disable after migration` comment. They will be disabled along with all other API scripts in Phase 3.

### 4. Order Form Before Save Complexity (9 merged scripts)
Nine separate Server Scripts all fire on Order Form Before Save:
`MOP Cash Terms Bypass`, `Auto-fill Approved By`, `Validate Term Request Change`, `Allow Delivery Address Edit for Admin`, `Price Edit`, `Price Modified Flag`, `Notes Acknowledgment Validation`, `Order Form Admin Edit Bypass`, and one more.

These must be merged into a single `before_save(doc, method)` function in `order_form.py`. Carefully read each body and preserve the logical ordering: access guards first, data mutation second, validation last.

### 5. Client Script Endpoint Update Window (Phase 3)
The 9 Client Scripts in the API dependency map must be updated in the same deployment window as api.py goes live. There is no grace period — the old `frappe.handler.run_server_script` endpoint is disabled immediately after the new endpoints are verified.

### 6. get_receivable_sales_for_customer Caller (unconfirmed)
The body of `get_receivable_sales_for_customer` states it is "used by Receipt Apply To grid." It does not appear in the auto-generated dependency map (likely because the call is inside a `set_query` callback, not a top-level `frappe.call`). Verify manually: search "get_receivable" in `Receipt: Form Controller` body before Phase 3.
