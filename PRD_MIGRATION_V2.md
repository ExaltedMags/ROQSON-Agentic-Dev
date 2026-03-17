# PRD: roqson_core Migration — Version 2

**Version**: 2.0 | **Created**: 2026-03-17 | **Status**: Approved — dev freeze in effect
**Supersedes**: PRD_MIGRATION.md (v1.0)
**Architecture ref**: ARCHITECTURE.md (generated from live discovery pass, 2026-03-17)

---

## Summary

Migrate all ROQSON ERPNext customizations from UI-based DocTypes (`Server Script`, `Client Script`, `Custom Field`) into a proper Frappe custom app (`roqson_core`). The app installs on the existing ROQSON-private-bench (confirmed Private Bench tier, custom app install supported) via the Frappe Cloud dashboard.

**Development freeze**: No changes to the live production instance until migration is complete and staging-validated. The freeze lifts in Phase 10.

**Key change from v1**: Script counts are updated from estimates to live-verified figures. Phase 0 adds a CSS injection audit step. Phase 5 has accurate per-DocType script counts and named module files.

---

## Environment

| Property | Value |
|---|---|
| Live site | `https://roqson-industrial-sales.s.frappe.cloud` |
| Frappe version | v15.x |
| Hosting | ROQSON-private-bench (Private Bench — confirmed) |
| API wrapper | `roqson.py` in this directory |
| Credentials | `.env` file (`ROQSON_API_KEY`, `ROQSON_API_SECRET`) |
| App name | `roqson_core` |
| App repo | Private GitHub repo — create before Phase 1 |
| Staging site | Create from production backup before Phase 3 |
| Architecture doc | `ARCHITECTURE.md` (read before any phase) |
| Script inventory | `_script_inventory.json` (raw discovery data) |

---

## Live Script Counts (authoritative — from 2026-03-17 discovery pass)

| Category | Active | Total |
|---|---|---|
| Server Scripts — DocType Event | **49** | 70 |
| Server Scripts — API | **26** | 35 |
| Server Scripts — Permission Query | **13** | 14 |
| Server Scripts — Scheduler Event | **2** | 7 |
| **Server Scripts total** | **90** | **127** |
| Client Scripts | **122** | 176 |

> v1 estimates were ~43 DocType Events, ~28 APIs, ~13 Permission Queries. The live counts are higher.

---

## Hard Constraints (Apply to Every Phase)

1. **Never rename a workflow state** — orphans existing documents; manual SQL recovery required.
2. **Never rename a DocType fieldname** — Frappe drops the old column, data is lost.
3. **Never change a field type in a fixture** — column type change may truncate data.
4. **Disabled scripts are dead code** — do not migrate `enabled=0` Client Scripts or `disabled=1` Server Scripts.
5. **Fixture `modified` timestamp must be newer than the DB record** — otherwise silently ignored, no error raised.
6. **API endpoint paths change** when Server Script APIs move to app Python — Client Scripts must be updated in the same deployment window (9 scripts known; verify `get_receivable_sales_for_customer` caller before Phase 3).
7. **Take a manual backup before every production deploy** — auto-backups are daily; you need a same-day backup.
8. **Read before write** — always fetch the current script before updating. Use `roqson.safe_update_script()`.
9. **`Trips` is the live DocType name** — CLAUDE.md and comments say "Trip Ticket" but the database DocType is `Trips`.
10. **Never delete a script** — set `enabled: 0` (Client Script) or `disabled: 1` (Server Script).

---

## Phase Overview

| Phase | Content | Risk | Script count | Prerequisite |
|---|---|---|---|---|
| 0 | Audit + snapshot all scripts | None | — | — |
| 0.5 | CSS injection audit (categorise 29 injecting CS) | None | 29 CS | Phase 0 complete |
| 1 | Scaffold `roqson_core` app skeleton on GitHub | None | — | Phase 0 complete |
| 2 | Create staging site from production backup | None | — | Phase 1 complete |
| 3 | Active API Server Scripts → `api.py` | Low | 26 SS + 9 CS | Staging live |
| 4 | Custom Fields + Print Formats → fixtures | Low | 44 CF + 2 PF | Staging live |
| 5 | DocType Event Server Scripts → Python modules | Medium | 49 SS | Phases 3 + 4 on staging + prod |
| 6 | Permission Query Scripts → `permissions.py` | Medium | 13 PQ + 2 misclassified | Phase 5 complete |
| 7 | Scheduler Scripts → `tasks.py` | Low | 2 SS | Phase 5 complete |
| 8 | DocType JSON → fixtures | High | 59 DocTypes | Phases 3–7 stable |
| 9 | Workflow JSON → fixtures | High | 4 Workflows | Phase 8 verified |
| 10 | Lift development freeze | — | — | Phase 9 verified |

---

## Phase 0: Audit & Local Snapshot

**Goal**: Capture the complete live state before touching anything. These snapshots are your rollback reference.

### Step 0.1 — Verify API connectivity
```bash
python roqson.py
```
Expected: `[OK] Connected. Found N recent error log entries.`

### Step 0.2 — Snapshot all scripts by DocType
```bash
python -c "import roqson; roqson.snapshot_scripts('Order Form')"
python -c "import roqson; roqson.snapshot_scripts('Trips')"
python -c "import roqson; roqson.snapshot_scripts('Sales')"
python -c "import roqson; roqson.snapshot_scripts('Customer Information')"
python -c "import roqson; roqson.snapshot_scripts('Credit Application')"
python -c "import roqson; roqson.snapshot_scripts('Credit Application Request')"
python -c "import roqson; roqson.snapshot_scripts('Receipt')"
python -c "import roqson; roqson.snapshot_scripts('Inventory Ledger')"
```

### Step 0.3 — Verify Server Script inventory
```python
import roqson, json
all_ss = roqson.list_docs(
    'Server Script',
    ['name', 'script_type', 'reference_doctype', 'disabled'],
    limit=200
)
active = [s for s in all_ss if not s.get('disabled')]
print(f"Total: {len(all_ss)}, Active: {len(active)}")
# Expected: Total ~127, Active ~90
by_type = {}
for s in active:
    t = s['script_type']
    by_type.setdefault(t, []).append(s['name'])
print(json.dumps(by_type, indent=2))
# Expected: DocType Event ~49, API ~26, Permission Query ~13, Scheduler Event ~2
```

### Step 0.4 — Verify Client Script inventory
```python
import roqson, json
cs = roqson.list_docs(
    'Client Script',
    ['name', 'dt', 'enabled'],
    filters=[['enabled', '=', 1]],
    limit=200
)
by_dt = {}
for s in cs:
    by_dt.setdefault(s['dt'], []).append(s['name'])
print(f"Active Client Scripts: {len(cs)}")
# Expected: ~122
print(json.dumps(by_dt, indent=2))
```

### Step 0.5 — Investigate the orphaned Inventory Entry Quantity script
```python
import roqson
doc = roqson.get_doc('Server Script', 'Inventory Entry Quantity')
print('reference_doctype:', doc.get('reference_doctype'))
print('doctype_event:', doc.get('doctype_event'))
print('script:', doc.get('script'))
```
If `reference_doctype` is empty, assign it to `Inventory Entry` manually in the live instance before Phase 5, or note it as a known gap. (This is the only DocType Event with no reference_doctype.)

### Exit condition
Snapshot JSON files written locally. Server Script count matches 90 active. Client Script count matches 122 active.

---

## Phase 0.5: CSS Injection Audit

**Goal**: Catalogue every Client Script that injects CSS into the page. This is a documentation step — no code changes.

From the discovery pass, **29 Client Scripts** inject CSS. Full list is in `ARCHITECTURE.md` § CSS Injection Audit.

### Step 0.5.1 — Confirm injection scope per script
For each of the 29 scripts, read its body and answer:
- Is the CSS scoped to a specific form element? Or global?
- Does it conflict with Frappe's built-in styles?
- Could it be replaced with a Frappe `frm.set_df_property()` call instead?

### Step 0.5.2 — Record findings in ARCHITECTURE.md
Update the CSS Injection Audit section with notes per script. No code changes yet — this feeds a future cleanup phase.

### Exit condition
All 29 scripts reviewed. Notes added to ARCHITECTURE.md CSS Injection section.

---

## Phase 1: Scaffold roqson_core App Skeleton

**Goal**: Create the Frappe app directory structure locally and push to a private GitHub repo.

No local Frappe bench is available — scaffold the structure manually using the exact file list in `ARCHITECTURE.md`.

### Step 1.1 — Create GitHub repo (manual, browser)
1. GitHub → New repository
2. Name: `roqson_core` | Visibility: Private | No README
3. Copy the SSH remote URL

### Step 1.2 — Create directory structure

Files to create (exact content from PRD_MIGRATION.md v1, Step 1.2):
- `roqson_core/setup.py`
- `roqson_core/MANIFEST.in`
- `roqson_core/requirements.txt`
- `roqson_core/roqson_core/__init__.py`
- `roqson_core/roqson_core/hooks.py` (skeleton — no doc_events or fixtures yet)
- `roqson_core/roqson_core/api.py` (empty)
- `roqson_core/roqson_core/tasks.py` (empty)
- `roqson_core/roqson_core/permissions.py` (empty)
- `roqson_core/roqson_core/modules.txt`
- `roqson_core/roqson_core/patches.txt`
- `roqson_core/roqson_core/fixtures/.gitkeep`

Also create empty module files (will be populated in Phase 5):
- `roqson_core/roqson_core/order_form.py`
- `roqson_core/roqson_core/trips.py`
- `roqson_core/roqson_core/credit_application.py`
- `roqson_core/roqson_core/customer_information.py`
- `roqson_core/roqson_core/sales.py`
- `roqson_core/roqson_core/receipt.py`
- `roqson_core/roqson_core/price_change_request.py`
- `roqson_core/roqson_core/cost_tier.py`
- `roqson_core/roqson_core/inventory_entry.py`
- `roqson_core/roqson_core/inventory_ledger.py`

### Step 1.3 — Push to GitHub
```bash
cd roqson_core
git init && git add . && git commit -m "chore: initial app scaffold"
git branch -M main
git remote add origin git@github.com:YOUR_ORG/roqson_core.git
git push -u origin main
```

### Exit condition
GitHub repo exists with the above structure. `git status` is clean.

---

## Phase 2: Create Staging Site

**Goal**: Spin up a staging site from production backup. All migration testing happens here first.

Follow Phase 2 from PRD_MIGRATION.md v1 (Steps 2.1–2.4) exactly. No changes from v1.

### Exit condition
Staging site up. `roqson_core` installed. Staging API returns 200.

---

## Phase 3: API Server Scripts → api.py

**Goal**: Port all **26** active API-type Server Scripts to `roqson_core/api.py`. Disable originals. Update **9** Client Scripts calling them in the same deployment window.

**Script mapping**: See `ARCHITECTURE.md` § api.py — 26 functions for the full name → Python function name table.

**Endpoint path change**:
- Old: `frappe.handler.run_server_script` with `script_name` argument
- New: `roqson_core.api.<function_name>` directly

### Step 3.1 — Get the full list of active API scripts
```python
import roqson, json
scripts = roqson.list_docs(
    'Server Script',
    ['name', 'reference_doctype', 'disabled'],
    filters=[['script_type', '=', 'API'], ['disabled', '=', 0]],
    limit=100
)
print(json.dumps([s['name'] for s in scripts], indent=2))
# Expected: 26 scripts
```

### Step 3.2 — Fetch and review each script body
```python
import roqson
doc = roqson.get_doc('Server Script', 'SCRIPT_NAME_HERE')
print(f"API method: {doc.get('api_method')}")
print(doc.get('script'))
```

Use the function names from `ARCHITECTURE.md` api.py table. Apply these transforms:
- Replace `frappe.response['message'] = X` with `return X`
- Replace string concatenation workarounds with f-strings
- Add needed `import` statements at the top
- Do not change business logic

### Step 3.3 — Verify get_receivable_sales_for_customer caller
Before deploying, search the Receipt: Form Controller body for this API call:
```python
import roqson
body = roqson.get_script_body('Client Script', 'Receipt: Form Controller')
print('get_receivable' in body)   # Expected: True (it is called here)
```
If True, add Receipt: Form Controller to the Phase 3.7c update list.

### Step 3.4 — Find all Client Scripts calling each API script

The **9 confirmed Client Scripts** that need endpoint updates:

| Client Script | Old script_name | New roqson_core.api path |
|---|---|---|
| Order Form: Stock Availability UX | `Get Product Stock API` | `roqson_core.api.get_product_stock` |
| CSF: Get Last Order | `CSF Get Last Order` | `roqson_core.api.get_last_outlet_order` |
| CSF: Add photos | `CSF: Add Photos` | `roqson_core.api.get_survey_photos` |
| Order Form Promos | `Get Promo Warehouse` | `roqson_core.api.get_promo_warehouse` |
| Full Order Script | `Get Active Trip Order Names` | `roqson_core.api.get_active_trip_order_names` |
| Full Order Script | `Timestamping` | `roqson_core.api.stamp` |
| Sales: Receipts Section | `get_receipt_history_for_sale` | `roqson_core.api.get_receipt_history_for_sale` |
| Order History Summary | `get_customer_orders` | `roqson_core.api.get_customer_orders` |
| Product: Show Inventory | `Product: Get Inventory` | `roqson_core.api.get_product_inventory` |

Prepare new bodies for each before the deployment window.

### Step 3.5 — Deploy to staging and test

Push api.py to GitHub, redeploy staging. Test each of the 9 endpoints:
```bash
curl -X POST 'https://roqson-staging.s.frappe.cloud/api/method/roqson_core.api.get_product_stock' \
  -H 'Authorization: token KEY:SECRET' \
  -H 'Content-Type: application/json' \
  -d '{"mode": "get_all_products"}'
```
Verify responses match what the old scripts returned. Also test RPM endpoints via the RPM admin page on staging.

### Step 3.6 — Production deploy (coordinated window)

**3.6.a** — Manual backup (Frappe Cloud → Sites → roqson-industrial-sales → Backups)

**3.6.b** — Deploy app to production bench

**3.6.c** — Update all 9 (or 10 if Receipt confirmed) Client Scripts:
```python
import roqson
roqson.safe_update_script('Client Script', 'Order Form: Stock Availability UX', new_body)
# Repeat for each
```

**3.6.d** — Verify each new endpoint works on production:
```python
import roqson
roqson.call_method('roqson_core.api.get_product_stock', mode='get_all_products')
```

**3.6.e** — Disable all 26 original API Server Scripts:
```python
import roqson
roqson.disable_script('Server Script', 'Get Product Stock API')
# Repeat for all 26
```

### Exit condition
- All 26 active API Server Scripts disabled
- All Client Scripts call `roqson_core.api.*` endpoints
- RPM admin page functions normally
- Error logs clean: `python -c "import roqson; roqson.print_error_logs(20)"`

---

## Phase 4: Custom Fields + Print Formats → Fixtures

**Goal**: Export **44** custom fields and **2** print formats as JSON fixtures.

No changes from PRD_MIGRATION.md v1 Steps 4.1–4.5.

**Confirmed counts from live discovery**:
- Custom Fields: 44 (across Trips, Address, Vehicle, Vehicles, Driver, Print Settings, Order Form, Sales, Promos, Contact)
- Print Formats: 2 (`Sales Billing Statement`, `Billing Statement`)

### Exit condition
Custom field count matches 44. Both print formats present. No new error log entries.

---

## Phase 5: DocType Event Server Scripts → Python Modules

**Goal**: Port all **49** active DocType Event Server Scripts to Python module files, wired through `hooks.py` `doc_events`. Proceed one DocType at a time in complexity order.

**Module files and script counts** (from live discovery):

| Module file | DocType | Script count | Complexity order |
|---|---|---|---|
| `receipt.py` | Receipt | 2 | 1st (simplest) |
| `cost_tier.py` | Cost Tier | 1 | 2nd |
| `price_change_request.py` | Price Change Request | 1 | 3rd |
| `inventory_entry.py` | Inventory Entry | 2 (incl. orphan — investigate) | 4th |
| `inventory_ledger.py` | Inventory Ledger | 2 | 5th |
| `sales.py` | Sales | 2 | 6th |
| `customer_information.py` | Customer Information | 3 | 7th |
| `credit_application.py` | Credit Application | 6 | 8th |
| `trips.py` | Trips | 8 | 9th |
| `order_form.py` | Order Form | 20 | 10th (most complex) |

> 2 scripts tagged as DocType Events but containing Permission Query logic (`Archive CI`, `Archive Sales Personnel`) are migrated in **Phase 6**, not here.

**Target hooks.py `doc_events` skeleton** is in `ARCHITECTURE.md` § hooks.py Skeleton.

### Step 5.0 — Verify module import path on staging (do this before any hooks)

Run in the staging System Console:
```python
import importlib, traceback
for path in ['roqson_core.receipt', 'roqson_core.roqson_core.receipt']:
    try:
        importlib.import_module(path)
        print(f"✓ Correct path: {path}")
        break
    except ModuleNotFoundError:
        print(f"✗ Not found: {path}")
```
Record the confirmed path: `__________________`
Use this prefix for all `doc_events` entries in hooks.py.

### Step 5.1 — Receipt (2 scripts)

Scripts:
- `Receipt: Revert Sales on Cancel` → `before_cancel(doc, method)`
- `Receipt: Update Sales on Submit` → `on_submit(doc, method)`

Fetch each body:
```python
import roqson
print(roqson.get_script_body('Server Script', 'Receipt: Revert Sales on Cancel'))
print(roqson.get_script_body('Server Script', 'Receipt: Update Sales on Submit'))
```

Create `receipt.py`, add `"Receipt"` to `doc_events` in hooks.py, push, deploy staging, test by submitting and cancelling a Receipt. Verify Sales outstanding_balance updates correctly.

Disable originals after staging passes and production deploy completes:
```python
import roqson
roqson.disable_script('Server Script', 'Receipt: Revert Sales on Cancel')
roqson.disable_script('Server Script', 'Receipt: Update Sales on Submit')
```

### Step 5.2 — Cost Tier (1 script)

Script: `Cost Tier: Display Name` → `before_save(doc, method)`

### Step 5.3 — Price Change Request (1 script)

Script: `Process PCR Approval` → `after_save(doc, method)`

Test by approving a PCR and confirming the Order Form state updates.

### Step 5.4 — Inventory Entry (1 script)

Script:
- `Inventory Stock In` → `after_insert(doc, method)`

### Step 5.5 — Inventory Ledger (3 scripts)

Scripts:
- `Source` → `before_insert(doc, method)`
- `Inventory Notifications` → `after_insert(doc, method)`
- `Inventory Entry Quantity` → `on_update_after_submit(doc, method)` — has no `reference_doctype` in live instance; set it to `Inventory Ledger` before Phase 5 (body confirmed: uses doc.product, doc.warehouse, doc.quantity)

### Step 5.6 — Sales (2 scripts)

Scripts:
- `Auto Cancel Order on Sales Cancellation` → `before_save(doc, method)`
- `Sales Inventory Stock Out` → `after_save(doc, method)`

Test by cancelling a Sales record and confirming the linked Order Form receives the cancellation.

### Step 5.7 — Customer Information (3 scripts)

Scripts:
- `CI: Unlimited Credit Set` → `before_save` (merged)
- `Customer Information: Fields Validation` → `before_save` (merged)
- `CI: Allow Edit After Subm` → `on_update_after_submit`

> `Archive CI` (the 4th script tagged as DocType Event for Customer Information) is misclassified and goes to Phase 6.

### Step 5.8 — Credit Application (6 scripts)

Scripts: `CA: Enforce Signatures`, `CA: Supporting Documents`, `CA: Minimum`, `CA: Update Credit Approval`, `CA: Needs Review Notificaton`, `CA: For Completion Notif`

Test by going through the full credit approval workflow on staging.

### Step 5.9 — Trips (8 scripts)

Scripts:
- `Trip Numbering` → `before_insert`
- `Fix Dispatch Time` → `before_validate`
- `Enforce Eligibility`, `Trip Ticket Multi-Driver Sync`, `Trip Ticket Transit Update`, `Delivery Status Notification` → `before_save` (merged, careful with ordering)
- `Trip Ticket Creation Notification` → `after_insert`
- `Trip Ticket and Order Form Traceability` → `after_save`

Test by creating a Trips record and running through the full delivery workflow.

### Step 5.10 — Order Form (20 scripts)

Scripts: see `ARCHITECTURE.md` § order_form.py — 20 functions for the full event mapping.

**Before Save — 9 scripts merge into one function**. The ordering matters: read all 9 bodies, determine logical sequence, merge carefully.

**After Save (Submitted Document) — 3+ scripts**. The `Approved, Rejected, Reserved...` script covers multiple workflow state transitions in a single body; preserve the full switch logic.

Test by going through the full Order Form workflow: Draft → Needs Review → Approved → Reserved → Dispatched → Delivered, plus Cancel path.

### Step 5.11 — Final verification
```python
import roqson, json
remaining = roqson.list_docs(
    'Server Script',
    ['name', 'reference_doctype'],
    filters=[['script_type', '=', 'DocType Event'], ['disabled', '=', 0]],
    limit=100
)
print(f"Still-active DocType Event scripts: {len(remaining)}")
# Expected: 2 (Archive CI and Archive Sales Personnel — these are migrated in Phase 6)
```

### Exit condition
47 of 49 DocType Event scripts disabled (2 remain for Phase 6). App hooks wired and tested on staging and production. Zero new error log entries.

---

## Phase 6: Permission Query Scripts → permissions.py

**Goal**: Port all **13** active Permission Query Server Scripts plus **2** misclassified DocType Events to `permissions.py`. Wire via `hooks.py` `permission_query_conditions`.

**Total functions in permissions.py**: 15 (see `ARCHITECTURE.md` § permissions.py — 15 conditions for the full mapping).

**Archive DocTypes pattern**: 12 of the 15 are simple archive filters applied only during link field search:
```python
def get_order_form_conditions(user=None):
    if frappe.form_dict.get("cmd") == "frappe.desk.search.search_link":
        return "`tabOrder Form`.`archived` = 0"
    return ""
```

**Exceptions** (more complex logic):
- `Archive Trip Ticket` — also filters by driver role
- `Sales Permission Query` — role-based access control for Sales, Accounting, Driver

### Step 6.1 — Get all active Permission Query scripts
```python
import roqson, json
scripts = roqson.list_docs(
    'Server Script',
    ['name', 'reference_doctype', 'disabled'],
    filters=[['script_type', '=', 'Permission Query'], ['disabled', '=', 0]],
    limit=50
)
print(json.dumps(scripts, indent=2))
# Expected: 13 scripts
```

Also fetch the 2 misclassified DocType Events:
```python
print(roqson.get_script_body('Server Script', 'Archive CI'))
print(roqson.get_script_body('Server Script', 'Archive Sales Personnel'))
```

### Step 6.2 — Port to permissions.py

For each script, add a function following the naming convention `get_<doctype_snake_case>_conditions(user=None) -> str`.

### Step 6.3 — Register all 15 in hooks.py permission_query_conditions

See `ARCHITECTURE.md` § hooks.py Skeleton for the full `permission_query_conditions` dict.

### Step 6.4 — Test on staging (reportview API)
```python
import requests, os
from dotenv import load_dotenv
load_dotenv()
key = os.environ['ROQSON_API_KEY']
secret = os.environ['ROQSON_API_SECRET']
r = requests.get(
    'https://roqson-staging.s.frappe.cloud/api/method/frappe.desk.reportview.get',
    params={'doctype': 'Order Form', 'fields': '["name","status"]', 'limit_page_length': 5},
    headers={'Authorization': f'token {key}:{secret}'}
)
print(r.status_code, r.json())
# Verify: Archived records are NOT in the result
```
Repeat for: Trips, Sales, Credit Application, Customer Survey Form, Customer Information, Product, Nature of Business, Promos, Discounts, Territories, Vehicles, Warehouses, Brands, Sales Personnel.

### Step 6.5 — Production deploy + disable originals

After staging passes:
1. Manual backup
2. Deploy to production
3. Run the reportview test against production
4. Disable all 13 Permission Query scripts + Archive CI + Archive Sales Personnel:
```python
import roqson
# Repeat for all 15
roqson.disable_script('Server Script', 'Archive Order Form')
roqson.disable_script('Server Script', 'Archive Trip Ticket')
# ...
roqson.disable_script('Server Script', 'Archive CI')
roqson.disable_script('Server Script', 'Archive Sales Personnel')
```

### Exit condition
All 15 conditions active. No archived records visible in list views. No new error log entries.

---

## Phase 7: Scheduler Scripts → tasks.py

**Goal**: Port **2** active Scheduler Event scripts to `tasks.py`.

**Scripts**:
- `Auto Archive Expired Promos` (Daily) → `auto_archive_expired_promos()`
- `Overheld Reservation Notification` (Hourly) → `notify_overheld_reservations()`

```python
scheduler_events = {
    "daily":  ["roqson_core.tasks.auto_archive_expired_promos"],
    "hourly": ["roqson_core.tasks.notify_overheld_reservations"],
}
```

Scheduler tasks cannot be triggered manually without bench access. Deploy to staging, check staging error logs 24–48 hours later. After confirming clean, deploy to production and disable originals.

### Exit condition
Both active Scheduler scripts disabled. Tasks wired in hooks.py. No log errors after one schedule cycle.

---

## Phase 8: DocType Fixtures (High Risk)

**Start only after Phases 3–7 are stable on staging and production.**

**Goal**: Export all **59** custom DocTypes as JSON fixtures.

No changes to the procedure from PRD_MIGRATION.md v1 Steps 8.1–8.5.

**Key rule**: Set `"custom": 0` and bump `"modified"` to `"2026-03-17T12:00:00.000000"` (or later) in every fixture.

### Exit condition
All 59 DocTypes have `custom=0`. Record counts unchanged. No schema errors in logs.

---

## Phase 9: Workflow Fixtures (High Risk)

**Start only after Phase 8 is verified on both staging and production.**

**Goal**: Export all **4** active workflows as JSON fixtures.

**Active workflows**:
1. `Order Workflow` (DocType: Order Form)
2. `Time in Time out` (DocType: Trips)
3. `Credit Approval` (DocType: Credit Application)
4. `Credit Application Request Workflow` (DocType: Credit Application Request)

No changes to the procedure from PRD_MIGRATION.md v1 Steps 9.1–9.5.

**Zero state name changes** — any rename orphans existing documents permanently. Export exact.

### Exit condition
All 4 workflows in fixtures. Zero orphaned documents on staging and production. All workflow transitions working.

---

## Phase 10: Lift Development Freeze

### Pre-lift checklist
```python
import roqson, json

all_ss = roqson.list_docs(
    'Server Script', ['name', 'script_type', 'disabled'], limit=200
)
still_active = [s for s in all_ss if not s.get('disabled')]
print(f"Still-active Server Scripts: {len(still_active)}")
# Expected: 0
```

- [ ] All 26 active API Server Scripts disabled — `api.py` endpoints active
- [ ] All 49 active DocType Event Server Scripts disabled — `hooks.py` wired (47 to Python modules + 2 misclassified moved to permissions.py)
- [ ] All 13 active Permission Query Server Scripts disabled + 2 misclassified DocType Events disabled — `permissions.py` wired (15 total)
- [ ] Both active Scheduler Scripts disabled — `tasks.py` wired
- [ ] Custom Field count: 44
- [ ] Both print formats present and rendering
- [ ] All 4 workflows operational, zero orphaned documents
- [ ] Error logs clean: `python -c "import roqson; roqson.print_error_logs(50)"`
- [ ] GitHub repo up to date: `cd roqson_core && git status` → clean

**All checks green**: announce that development on `roqson_core` is open. New scripts and logic go into the app. No new UI-created Server Scripts or Client Scripts should be added going forward.

---

## Rollback Procedures

Identical to PRD_MIGRATION.md v1 § Rollback Procedures.

Key points:
- **Code-only rollback**: Frappe Cloud → Bench → Apps → roqson_core → View versions → Redeploy previous commit
- **DB-level rollback**: Restore from the manual backup taken before the phase
- **Emergency re-enable**:
```python
import roqson
roqson.update_doc('Client Script', 'Script Name', {'enabled': 1})
roqson.update_doc('Server Script', 'Script Name', {'disabled': 0})
```

---

## Verification Commands Reference

```python
# API connectivity
python roqson.py

# Active Server Scripts by type
import roqson, json
ss = roqson.list_docs('Server Script', ['name', 'script_type', 'disabled'], limit=200)
active = [s for s in ss if not s.get('disabled')]
by_type = {}
for s in active:
    by_type[s['script_type']] = by_type.get(s['script_type'], 0) + 1
print(f"Active: {len(active)}", json.dumps(by_type))
# Expected at Phase 10: Active: 0

# Active Client Scripts
import roqson
cs = roqson.list_docs('Client Script', ['name'], filters=[['enabled', '=', 1]], limit=200)
print(f"Active Client Scripts: {len(cs)}")
# Expected throughout: ~122 (Client Scripts are NOT disabled during migration)

# Recent error logs
import roqson
roqson.print_error_logs(30)

# Test a production API endpoint
import roqson
roqson.call_method('roqson_core.api.get_product_stock', mode='get_all_products')

# Test Permission Query
import requests, os
from dotenv import load_dotenv
load_dotenv()
r = requests.get(
    'https://roqson-industrial-sales.s.frappe.cloud/api/method/frappe.desk.reportview.get',
    params={'doctype': 'Order Form', 'fields': '["name","status"]', 'limit_page_length': 5},
    headers={'Authorization': f'token {os.environ["ROQSON_API_KEY"]}:{os.environ["ROQSON_API_SECRET"]}'}
)
print(r.status_code, r.json())
```
