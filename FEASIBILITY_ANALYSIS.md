# ROQSON ERPNext: Custom App Migration & Offline PWA Feasibility Analysis

**Date**: 2026-03-15
**Scope**: Frappe v15 / ERPNext 15 on Frappe Cloud
**Objective**: Evaluate moving from UI-based customizations to a custom Frappe app + offline-capable field app

---

## Executive Summary

| Question | Answer | Confidence |
|---|---|---|
| **Should we migrate to a custom app now?** | Not yet — but plan a phased approach starting with scripts & fixtures only | High |
| **Is offline mode feasible?** | Yes, as a read-heavy companion app. Full offline-first requires the custom app. | High |
| **What's the migration risk level?** | Medium-to-High on DocTypes; Low on scripts/fields. Plan 2–3 month rollout with staging bench. | High |
| **Do we need to upgrade hosting?** | Confirm if on **Private Bench** (app-capable) vs. Shared Hosting (app-restricted). $25/mo tier exists for both. | Critical |

---

## Audit Summary

### Custom DocTypes (59 total)

| Module | Count | Key DocTypes |
|---|---|---|
| **Selling** | 38 | Order Form, Sales, Customer Information, Credit Application, Trips, Product, Promos, Discounts, etc. |
| **Stock** | 12 | Inventory Ledger, Inventory Entry, Warehouses, Cost Tier, Trip Ticket Failed Deliveries |
| **Custom/Customer** | 9 | Receipt, Receipt Apply To, PH Address, PH Barangay, PH City Municipality, PH Province, Drivers |

**Observations:**
- 59 custom doctypes represents a **full ERP domain**, not a simple extension
- `Trips` is the live DocType name (internally called "Trip Ticket" in docs/comments)
- Some apparent legacy/draft doctypes exist (Order, Sales Order Form, DSP Order Form, Customer Management) — likely superseded but still present
- Module assignments inconsistent: Receipt/Receipt Apply To in "Custom"; PH Addresses in mixed modules

---

### Server Scripts (117 total)

#### By Type
| Script Type | Active | Disabled | Total | Migration Path |
|---|---|---|---|---|
| **DocType Event** | 43 | 21 | 64 | `hooks.py` → `doc_events` dict |
| **API** | 28 | 9 | 37 | `{app}/api.py` + `@frappe.whitelist()` |
| **Permission Query** | 13 | 1 | 14 | `hooks.py` → `permission_query_conditions` |
| **Scheduler Event** | 2 | 5 | 7 | `{app}/tasks.py` |

#### Top DocTypes by Active Server Scripts
| DocType | Active Events | Disabled | Risk Level |
|---|---|---|---|
| Order Form | 14 | 7 | Medium |
| Trips | 9 | 3 | Medium |
| Credit Application | 6 | 1 | Low |
| Sales | 3 | 0 | Low |
| Customer Information | 4 | 1 | Low |
| Receipt | 2 | 0 | Low |

**Key Finding**: Order Form and Trips are heavily scripted. These will require the most audit work during migration.

---

### Client Scripts (190 total)

#### By DocType
| DocType | Enabled | Disabled | Total | Notes |
|---|---|---|---|---|
| Order Form | 32 | 28 | 60 | Largest surface; ~28 dead/draft scripts |
| Trips | 11 | 12 | 23 | Mixed state; 12 disabled scripts are legacy |
| Credit Application | 10 | 4 | 14 | Mostly production-ready |
| Customer Information | 8 | 0 | 8 | Clean, all active |
| Customer Survey Form | 7 | 2 | 9 | Mostly active |
| Inventory Ledger | 6 | 0 | 6 | Clean, all active |
| Sales | 6 | 0 | 6 | Clean, all active |
| Warehouses, SP, Brands, etc. | 22 | 0 | 22 | Archive/archive-list scripts |

**Key Finding**: ~50+ disabled Client Scripts are dead code that should NOT be migrated. They're taking up mental overhead and adding confusion during refactoring.

---

### Active Workflows (4)

| Workflow | DocType | Status | Complexity |
|---|---|---|---|
| Order Workflow | Order Form | Active | High (multiple state transitions) |
| Time in Time out | Trips | Active | Medium (delivery flow) |
| Credit Approval | Credit Application | Active | Low (simple approval chain) |
| Credit Application Request Workflow | Credit Application Request | Active | Low (simple request flow) |

**Migration Risk**: HIGH — existing documents with `workflow_state` values must be preserved. Renaming or removing workflow states orphans documents.

---

### Custom Fields (44 total)

| DocType | Count | Type | Notes |
|---|---|---|---|
| Trips | 10 | Extended | Trip-specific fields |
| Address | 7 | Integration | PH address hierarchy integration |
| Vehicle | 7 | Extended | Extended vehicle fields |
| Vehicles | 5 | Custom DT | Extra vehicle fields on custom doctype |
| Driver | 3 | Extended | Driver extensions |
| Print Settings | 3 | Config | Custom print configuration |
| Order Form | 2 | — | Minor additions |
| Others | 7 | Scattered | Sales, Promos, Contact, etc. |

**Migration Risk**: LOW — custom fields are the safest to migrate. Frappe handles schema merging gracefully.

---

### Custom Print Formats (2 relevant)

| Name | DocType | Status |
|---|---|---|
| Sales Billing Statement | Sales | Custom |
| Billing Statement | Trips | Custom |

**Migration Risk**: LOW — pure definition records with no state.

---

## Custom App Migration: What Changes

### Per Customization Type

#### Custom DocTypes
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Custom DocTypes (59)** | `custom=1` in DB | Export as JSON fixtures → `fixtures/` dir in app | **HIGH** | See Fixture Conflicts section. DocTypes with production data need ownership transfer, not recreation. |

**Migration Strategy:**
- Do NOT migrate all 59 at once
- Start with new DocTypes (Receipt, Receipt Apply To, PH Address hierarchy) that don't have legacy UI-created versions
- Leave existing core DocTypes (Order Form, Sales, Trips) alone initially — they work and have production data
- Phase 2: Add core DocTypes to fixtures after staging validation

---

#### Server Scripts — DocType Events
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **DocType Events (64)** | In `Server Script` DocType, run in `safe_exec` sandbox | Move to `{app}/hooks.py` → `doc_events` dict + `.py` module files | **MEDIUM** | Sandbox restrictions disappear (f-strings, imports, format() all work now). Behavior can change if scripts relied on RestrictedPython quirks. Must audit all 43 active scripts for unintended RestrictedPython workarounds that are now unnecessary. |

**Sandbox Restrictions Removed:**
- ✅ Now allowed: `import` statements, f-strings, `.format()`, arbitrary Python stdlib
- ⚠️ Your current workarounds (string concatenation instead of f-strings, for-loops instead of generators) still work — they just become unnecessarily verbose
- ✅ `frappe.db.sql()` parameterization remains the same (`%s` patterns)

**Migration Audit Checklist:**
- [ ] For each Server Script, check if it uses string concatenation instead of f-strings → simplify to f-strings
- [ ] Check if it uses `for` loops instead of generators/comprehensions → consider simplifying
- [ ] Check for direct `frappe.db.sql()` calls → verify parameterization is correct (`%s` placeholders)
- [ ] Check for `frappe.db.get_value()` calls that fetch data for use in loops → consider refactoring to `get_list()` with proper filtering

---

#### Server Scripts — API
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **API Scripts (37)** | In `Server Script` DocType, endpoint is `/api/method/frappe.handler.run_server_script` | Move to `{app}/api.py` with `@frappe.whitelist()` decorator. Endpoint becomes `/api/method/{app_name}.api.{function_name}` | **LOW** | Direct port. Client Scripts referencing these endpoints will break unless endpoint paths are updated in sync. |

**Client Script Breakage Example:**
```javascript
// OLD (Server Script API)
frappe.call({
  method: 'frappe.handler.run_server_script',
  args: { script_name: 'Get Product Stock API', ... }
});

// NEW (App API)
frappe.call({
  method: 'roqson_core.api.get_product_stock',
  args: { ... }
});
```

**Mitigation:**
- Update all Client Script references to new endpoint paths during migration
- OR: Create wrapper endpoints in Server Scripts that call app APIs (for gradual migration)

---

#### Server Scripts — Permission Query
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Permission Queries (14)** | In `Server Script` DocType, script_type='Permission Query' | Move to `{app}/hooks.py` → `permission_query_conditions` dict + custom permission modules | **MEDIUM** | Archive logic (13 active) currently uses filter injection via Permission Query. The app equivalent is `permission_query_conditions` in hooks. Functionally identical if ported carefully. |

**Archive Logic Example:**
```python
# Server Script (Permission Query)
frappe.flags.archive_table = "Order Form"
frappe.db.set_value("Order Form", docname, "status", "Archived")

# App hooks.py
def get_order_form_conditions(user):
    return "(`tabOrder Form`.status != 'Archived')"

permission_query_conditions = {
  "Order Form": "get_order_form_conditions",
}
```

---

#### Server Scripts — Scheduler
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Scheduler Events (7, 2 active)** | In `Server Script` DocType, script_type='Scheduler Event' | Move to `{app}/tasks.py` + scheduler hooks in `hooks.py` | **LOW** | Direct port. Cron syntax identical. |

**Example:**
```python
# hooks.py
scheduler_events = {
  "daily": [
    "roqson_core.tasks.auto_archive_expired_promos",
  ]
}
```

---

#### Client Scripts
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Client Scripts (190)** | In `Client Script` DocType | Move active scripts to `{app}/public/js/{doctype}.js` + hooks | **MEDIUM** | ~90 disabled scripts are dead weight — don't migrate them. Active scripts reference `/api/method/` endpoints; if Server Script API paths change, these all break in sync. Need coordinated migration. |

**Dead Code to Skip:**
- ~28 Order Form disabled scripts
- ~12 Trips disabled scripts
- Any script with `enabled=0` in the live audit

**Migration Strategy:**
- Create app hook for Client Scripts: `app_include_js = { "doctype": ["path/to/script.js"] }`
- Keep Server Script path updates in sync with Client Script endpoint calls
- Test each doctype's script bundle after migration

---

#### Workflows
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Workflows (4)** | In `Workflow` DocType, custom=1 or custom=0 | Export as Workflow JSON fixtures → `fixtures/` dir | **HIGH** | See Workflow State Ownership section. Existing documents with `workflow_state` values must match new workflow state names exactly, or docs enter orphaned state. Requires staging validation. |

**Workflow State Preservation Risk:**
- Documents retain their `workflow_state` string value as-is
- If a state is renamed in the fixture (e.g., "Draft" → "New"), existing docs with `workflow_state="Draft"` become orphaned
- Workflow action buttons won't render on orphaned docs
- **No automatic migration path** — manual script needed if states change

**Safe Approach:**
- Export each workflow exactly as it exists today (no renames)
- Install on staging site first
- Verify all documents still have valid workflow states
- Only then promote to production

---

#### Custom Fields
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Custom Fields (44)** | Scattered across Trips, Address, Vehicle, etc. | Export as Custom Field JSON fixtures → `fixtures/` dir | **LOW** | Safest migration type. Frappe handles merge/update gracefully. |

---

#### Print Formats
| Item | Current State | Migration Path | Risk | Notes |
|---|---|---|---|---|
| **Print Formats (2)** | In `Print Format` DocType | Export as Print Format JSON fixtures → `fixtures/` dir | **LOW** | Pure definition records, no state. |

---

## Fixture Conflicts: The Critical Issue

### What Happens When You Install a Fixture Over a Custom DocType

When you install a Frappe app that ships a DocType JSON as a fixture, `bench migrate` calls `frappe.sync_fixtures()`. Here's the actual behavior:

#### Scenario 1: DocType exists as `custom=1` in DB, app provides fixture
- Frappe compares the JSON fixture against the live DB record
- **Field-level merge**: Fields in fixture but missing in DB → added. Fields in DB but absent from fixture → left alone (not deleted)
- **The `custom` flag is NOT automatically cleared** — you must set `"custom": 0` in the fixture JSON
- **CRITICAL**: The fixture's `"modified"` timestamp must be **newer than** the DB record's `"modified"` value
  - If fixture timestamp ≤ DB timestamp, **the fixture is silently ignored** and no error is raised
  - Result: You think you migrated, but nothing changed

#### Scenario 2: DocType deleted from DB, fixture is installed
- Clean migration — Frappe creates the DocType from fixture
- No conflicts possible

#### Scenario 3: Conflict Detection
- **There is NO built-in conflict detection or merge UI**
- If timestamps don't align, fixture is silently skipped
- If field definitions diverge (UI edits vs. fixture), the behavior is unpredictable

### Safe Migration Path

```
Step 1: Export Current State
  $ bench --site roqson-industrial-sales.s.frappe.cloud export-fixtures

Step 2: Prepare Fixture JSON
  - Set "custom": 0 in the fixture
  - Set "modified": "2026-03-15T12:00:00" (current datetime, ISO format)
  - Review all fieldnames — ensure they match the live DB (SELECT * FROM information_schema.COLUMNS WHERE TABLE_NAME='tab<DocType>')

Step 3: Test on Staging Bench
  - Create a staging site from production backup
  - Install app with fixture → bench migrate
  - Verify no errors in logs
  - Verify field data is intact

Step 4: Production Install
  - Backup production site
  - Install app → bench migrate
  - Verify in Frappe console:
    frappe.db.get_value("DocType", "Order Form", "custom")  # should return 0

Step 5: Clean Up Custom Flag (Optional)
  - If doctype still shows custom=1 in UI, manually set via console:
    frappe.db.set_value("DocType", "Order Form", "custom", 0)
```

---

## Server Script Sandbox Restrictions vs. App Python

### Server Script Restrictions (RestrictedPython)

**Allowed:**
- `json` module (whitelisted explicitly)
- Frappe ORM: `frappe.get_doc()`, `frappe.db.get_value()`, etc.
- Validation: `frappe.ValidationError`, `frappe.flags`, `frappe.throw()`
- Response: `frappe.response['message']`
- Document methods: `doc.save()`, field access

**NOT Allowed:**
- `import` statements (only `json` is whitelisted)
- `format()` built-in function
- **F-strings** (RestrictedPython limitation)
- `.format()` method on strings → must use string concatenation
- Most Python standard library (`os`, `subprocess`, `requests`, etc.)
- Nested attribute access for escaping sandbox

### When Migrated to App Python

**All restrictions are lifted:**
- Full `import` access — can use any stdlib or third-party package
- F-strings work
- `.format()` works
- You write normal Python event handlers: `def before_save(self):`, etc.

### Behavioral Differences to Watch

| Aspect | Server Script | App Python |
|---|---|---|
| **Imports** | Restricted | Full access |
| **F-strings** | Not allowed | ✅ Works |
| **format()** | Not allowed | ✅ Works |
| **SQL Parameters** | `%s` placeholders (RestrictedPython enforced) | Same; you must parameterize manually |
| **Return values** | Set `frappe.response['message']` | Return normally or set `frappe.response` |
| **Error handling** | `frappe.throw()` | `raise frappe.ValidationError()` or `frappe.throw()` |
| **Performance** | Sandboxed, slightly slower | Native Python, faster |

### Migration Gotchas

**Your current code uses workarounds for RestrictedPython limitations:**

```python
# Current Server Script (RestrictedPython workaround)
result = ""
for item in items:
    result = result + item.name + " "  # String concatenation instead of f-string

# Post-migration (simplified)
result = " ".join(item.name for item in items)  # Much cleaner
```

All such workarounds still work in app code — they just become unnecessary verbose. You can refactor them gradually or leave as-is.

---

## Workflow State Ownership

### Current State
Workflows are stored in the `Workflow` DocType. When created via the web UI:
- `custom=1` flag is set
- Stored as a DB record (not version-controlled)
- `workflow_state` values in documents are simple string references to workflow state names

### What Happens on Fixture Install

When you install an app that defines a workflow as a fixture:
1. `bench migrate` calls `frappe.sync_fixtures()` → overwrites the `Workflow` record with the fixture version
2. Existing documents **retain their `workflow_state` string values** (they are NOT reset)
3. **If the fixture redefines states with different names**, existing doc states become **orphaned**
   - Example: You rename "Draft" → "New" in the workflow fixture
   - Existing docs with `workflow_state="Draft"` still have that value
   - The workflow definition no longer has a "Draft" state
   - Workflow action buttons don't render for those docs — they're stuck

### Safe Approach: No Breaking Changes

**Export the workflow exactly as it exists, make zero changes to state names:**

```json
{
  "doctype": "Workflow",
  "name": "Order Workflow",
  "document_type": "Order Form",
  "workflow_state_field": "workflow_state",
  "states": [
    { "state": "Draft", "doc_status": "0" },
    { "state": "Submitted", "doc_status": "1" },
    { "state": "Approved", "doc_status": "1" },
    ...
  ],
  "transitions": [...]
}
```

Then:
1. Install on staging bench
2. Verify no docs become orphaned
3. Test all workflow actions (buttons render, transitions work)
4. Only then promote to production

---

## Data Continuity for Production DocTypes

### How DocType Table Names Work

- DocType `Order Form` → underlying MariaDB table `tabOrder Form`
- When ownership moves from `custom=1` (UI) to app fixture, **the table name does NOT change**
- `bench migrate` runs `frappe.db.updatedb()` which alters the schema (adds/drops columns) but not the table name
- **Existing row data is preserved** as long as field definitions are compatible

### Data Loss Risk Scenarios

**Scenario 1: Field rename in fixture**
```json
// DB field: fieldname: "old_field_name"
// Fixture: fieldname: "new_field_name"
// Result: Frappe drops old_field_name, adds new_field_name
// DATA LOSS for old_field_name column
```

**Scenario 2: Field type change in fixture**
```json
// DB field: fieldtype: "Data"
// Fixture: fieldtype: "Link"
// Result: Frappe attempts to alter column type
// May fail or truncate data depending on DB compatibility
```

**Scenario 3: Child table field changes**
```
If a child table (like Order Details Table) changes fieldname or type,
data in that child table rows can be lost.
```

### Safe Migration Validation

Before installing a fixture on DocTypes with production data:

```bash
# Get current field list from DB
SELECT COLUMN_NAME, COLUMN_TYPE FROM information_schema.COLUMNS
WHERE TABLE_NAME='tabOrder Form';

# Compare against fixture JSON fieldnames
# If any fieldname is renamed or type is changed → DATA LOSS RISK
# Mitigation: Add a data migration script to rename/convert data before migrating schema
```

### Mitigation: Pre-Migration Script

For any field that's changing:
```python
# Add this as a migration hook in app before installing fixtures
def migrate_rename_field():
    # Copy old_field data to new_field
    frappe.db.sql("""
        UPDATE `tabOrder Form` SET new_field_name = old_field_name
    """)
    # Clean up or keep old field (depends on strategy)
```

---

## Frappe Cloud Rollback & Recovery

### Option 1: Restore from Backup

**Frappe Cloud Dashboard:**
1. Site → Restore & Migrate Site
2. Upload previous backup (database, public/private files)
3. Frappe Cloud applies the restore
4. Site reverts to backup point-in-time state

**Requirement**: You must have saved a manual backup BEFORE the breaking change.

### Option 2: Redeploy Previous App Version

**Frappe Cloud Dashboard:**
1. Bench → Deploy page → App list
2. Three-dot menu → view app versions
3. Click redeploy on previous version
4. Frappe Cloud runs `bench get-app --force {repo}@{old_commit}` + `bench migrate`

**Caveat**: This redeploys the app code to a previous version but does NOT restore the database. If the app install corrupted the DB schema, redeploy won't fix it — you need backup restore.

### Critical: Prepare Backups in Advance

**Frappe Cloud auto-backup**: Daily backups are saved, but if an install breaks the site on day 1, the latest auto-backup is from day 0 (could be up to 24 hours old — you lose 1 day of data).

**Procedure:**
```
1. Day 0 at 11:00 — Manual backup (Site → Backups → Create backup)
2. Day 0 at 11:15 — Install app
3. Day 0 at 11:16 — Verify no breakage
4. Day 1+ — Auto-backups continue
```

### No Automatic Rollback

- **There is no "undo last action" button** in Frappe Cloud
- **There is no automatic version history** with one-click rollback
- Rollback only works if you have:
  - A manual backup created before the change, OR
  - A previous app version in git that you can redeploy

---

## Offline Feasibility: Verdict

### YES — Viable as a read-heavy companion app. PARTIAL — Full offline-first needs custom app.

#### What Works Today (No Custom App Needed)

| Capability | Available | Notes |
|---|---|---|
| **Token Auth** | ✅ Yes | `Authorization: token key:secret` header. Works from any origin via REST API. |
| **REST Bulk Fetch** | ✅ Yes | `/api/resource/{DocType}?limit_page_length=500&fields=[...]`. Max 500 per call; paginate with `limit_start`. |
| **HTTPS** | ✅ Yes | Frappe Cloud provides TLS on all sites. Required for service workers. |
| **IndexedDB + Service Worker Pattern** | ✅ Yes (browser-side) | Standard PWA architecture. Nothing Frappe-specific blocks this. |
| **frappe.client.get_list** | ✅ Yes | REST equivalent. Supports filters, fields, pagination. |
| **Cached Offline Reads** | ✅ Yes | Service worker caches assets + API responses. Offline reads from cache. |

#### What Requires a Custom App

| Capability | Requires App | Why |
|---|---|---|
| **Serve PWA from same origin** | **Recommended** | Custom app can serve `index.html` + JS bundle at a Frappe route. Eliminates CORS. Alternatively: use a Frappe Page DocType (UI-creatable, but limited to simple static HTML/JS). |
| **CORS Configuration** | No | Can configure via Frappe Cloud dashboard → Site config → `allow_cors` setting. But same-origin is cleaner. |
| **Custom Sync Endpoints** | ✅ Yes | For conflict resolution, bulk upsert, custom write logic → need `/api/method/{app}.sync.bulk_push` |
| **Push Notifications** | ✅ Yes | Frappe notification hooks require server-side code in app |
| **Service Worker Registration** | Optional | Frappe v15 has a `Service Worker` DocType. The [PWA Frappe marketplace app](https://cloud.frappe.io/marketplace/apps/pwa_frappe) automates manifest + service worker config (installable on Private Bench via dashboard). |

### CORS Gotcha

Frappe Cloud does NOT add permissive CORS headers by default.
- **Cross-origin PWA** (served from different domain) → will hit CORS errors on requests with `Authorization` header (non-simple request)
- **Same-origin PWA** (served from `roqson-industrial-sales.s.frappe.cloud/trip-app`) → no CORS, full API access

**Workaround**: Configure `allow_cors` in site config via Frappe Cloud dashboard, but same-origin is preferred.

### Minimum DocType Surface for Trip Ticket Field App

Based on the audit, a delivery field app needs read/write access to:

| DocType | Access | Purpose |
|---|---|---|
| Trips | Read/Write | Load assigned trips for the day, update delivery status |
| Trips Table (child) | Read/Write | Per-order delivery status rows (Delivered/Failed) |
| Order Form | Read | Display order details (customer, items, address) |
| Order Details Table | Read | Line items for invoice display |
| Sales | Read/Write | Update status (In Transit → Received/Failed) |
| Customer Information | Read | Customer name, phone, address, credit terms |
| PH Address | Read | Delivery address lookup |
| Customer Survey Form | Create/Write | Create post-delivery survey |

**Estimated data size**: ~500–1,000 records across these doctypes for a single DSP's assigned territory. Feasible for IndexedDB on mobile.

### Offline Sync Architecture

**Recommended pattern (no custom app needed):**

```
1. Login: User authenticates with API key/secret → get token
2. Pre-load: Service worker caches all read-only data for DSP's territory into IndexedDB
3. Offline: User views trips, marks deliveries as Delivered/Failed locally
4. Queued writes: Service worker stores writes in LocalStorage as a queue
5. Online: Background Sync API triggers POST to `/api/resource/Trips/{id}` with updated status
6. Conflict handling: Last-write-wins (naive), or custom app endpoint for server-side conflict resolution
```

**Service Worker features:**
- Asset caching (JS, CSS, images)
- Stale-while-revalidate cache strategy for API responses
- Background sync for queued writes

**Frappe v15 has:**
- `Service Worker` DocType for configuration
- [PWA Frappe marketplace app](https://cloud.frappe.io/marketplace/apps/pwa_frappe) for automated setup

---

## Migration Risks & Gotchas

### Risk 1: Fixture Conflicts → Data Loss

**What can go wrong:**
- Fixture `modified` timestamp is older than DB record → fixture silently ignored, migration fails silently
- Field is renamed in fixture → old column dropped, data lost
- DocType stays with `custom=1` flag after install → hybrid ownership, unpredictable behavior

**Mitigation:**
- [ ] Bump `modified` timestamp in all fixtures to current datetime (ISO format)
- [ ] Validate field names against live DB schema BEFORE installing
- [ ] Test on staging bench BEFORE production
- [ ] After install, verify `custom=0` flag is set via System Console
- [ ] Take manual backup BEFORE any fixture install

---

### Risk 2: Server Script Sandbox Changes → Behavior Shifts

**What can go wrong:**
- Code that relied on RestrictedPython quirks behaves differently in app Python
- Example: a script that manually checked if an import was available (to detect sandbox environment) will now import successfully
- Example: a script that caught a `NameError` for generator scope issues will no longer catch that error

**Mitigation:**
- [ ] Audit all 43 active Server Scripts for RestrictedPython-specific workarounds
- [ ] Test on staging bench with realistic data
- [ ] Have rollback plan (redeploy previous app version, or restore DB)

---

### Risk 3: Workflow State Orphaning → Documents Stuck

**What can go wrong:**
- Workflow states are renamed in fixture → existing documents with old state names enter orphaned state
- Workflow action buttons don't render → docs become stuck, can't transition
- No easy way to bulk-migrate document states

**Mitigation:**
- [ ] Export workflow exactly as it exists (zero state name changes)
- [ ] Test on staging bench → verify all documents still have valid workflow states
- [ ] Write a migration script if any state MUST be renamed:
  ```python
  frappe.db.sql("""
    UPDATE `tabOrder Form` SET workflow_state='New' WHERE workflow_state='Draft'
  """)
  ```

---

### Risk 4: Custom Field Migration → Data Loss on Type Change

**What can go wrong:**
- Custom field type is changed in fixture → DB column type changes → data truncation
- Custom field name is changed in fixture → old column dropped, new column added, data lost

**Mitigation:**
- [ ] Never change field type or name in fixture (unless you have a data migration script)
- [ ] Validate all custom field definitions match DB schema
- [ ] Test on staging bench

---

### Risk 5: Frappe Cloud $25/mo Tier Limitations

**What can go wrong:**
- You attempt to install a custom app but you're on **Shared Hosting** (no custom app support)
- You assume Private Bench is available at $25/mo, but it's actually $50+/mo

**Clarification:**
- **Shared Hosting** (~$25/mo): Single site, no custom apps, limited config
- **Private Bench** (~$25/mo for entry tier): Multiple sites, custom apps via dashboard, more config

**Check your current tier:**
- Log into Frappe Cloud dashboard
- Look for "Bench" in the sidebar (if present → Private Bench)
- Or look at your Sites page — if you see "Your site is on a shared bench" → Shared Hosting

**If on Shared Hosting**: You must upgrade to Private Bench tier before installing a custom app.

---

### Risk 6: Rollback Without Backup → Unrecoverable

**What can go wrong:**
- App install breaks production site
- No manual backup was taken beforehand
- Only automatic backup is from 24 hours ago (data loss)

**Mitigation:**
- [ ] Take manual backup via Frappe Cloud dashboard immediately before any install
- [ ] Verify backup file is available (Backups tab)
- [ ] Have rollback procedure documented and tested on staging
- [ ] Set up slack/email alerts for app install events (if available in plan)

---

## Recommendation

### Question 1: Is a full migration to a custom app worth it?

**Short Answer: Not yet — but plan a phased approach starting with low-risk items.**

**Rationale:**
- Current setup is functional and production-stable
- Full migration (59 DocTypes + 117 Server Scripts + 190 Client Scripts → app) is a **2–3 month project** for a single developer
- Main benefits (version control, debuggable Python, CI/CD) are long-term wins, not day-one emergencies
- Risks (fixture conflicts, workflow orphaning, data loss) are real and non-trivial

**When to migrate:**
- You need custom sync logic for the offline app → need custom app
- You want version control over scripts → need custom app
- You're adding complex new logic that benefits from proper Python ecosystem → need custom app

---

### Question 2: Minimal Viable Custom App Scope

**Recommended First App: `roqson_core` — Scripts & Fixtures Only**

**Scope (Phase 1 — low risk):**

1. **Move API Server Scripts to app Python** (37 scripts)
   - Gain: imports, f-strings, debuggability, testability
   - Risk: LOW (API scripts are stateless)
   - Effort: ~1 week
   - Deliverable: `roqson_core/api.py` with all API endpoints

2. **Export Custom Fields as fixtures** (44 fields)
   - Gain: version control, schema auditability
   - Risk: LOW (fields are safe to migrate)
   - Effort: ~1 day
   - Deliverable: `roqson_core/fixtures/custom_field_*.json`

3. **Export Print Formats as fixtures** (2 formats)
   - Gain: version control
   - Risk: LOW (no state, pure definition)
   - Effort: ~1 hour
   - Deliverable: `roqson_core/fixtures/print_format_*.json`

4. **Leave DocType ownership alone** — custom=1 DocTypes stay as-is
5. **Leave Workflows alone** — they work, don't touch them yet

**Benefits of Phase 1:**
- Version control over your most change-prone items (scripts)
- Ability to write proper Python (imports, f-strings, testing)
- No risky DocType or workflow migrations
- Can be installed and uninstalled safely
- If something breaks, just uninstall and redeploy previous version

**Timeline:**
- ~1–2 weeks of work
- 1–2 days on staging bench
- 1 day production install

---

### Question 3: Is offline mode feasible now?

**Short Answer: Yes for a read-heavy companion app. Build it incrementally.**

**Phase 1 (No custom app needed) — Trip Ticket Companion PWA:**

1. **Build a PWA served from Frappe Page** (UI-creatable, no custom app)
   - Simple single-page HTML + JS bundle
   - Serves from `roqson-industrial-sales.s.frappe.cloud/{page_url}`
   - No CORS issues

2. **Integrate Frappe REST API** with token auth
   - Pre-load Trips, Order Form, Customer Information for DSP's territory
   - Cache into IndexedDB via service worker

3. **Offline reads** work from IndexedDB cache
   - Delivery details visible without connection

4. **Offline writes** queued in LocalStorage
   - Status updates stored locally while offline

5. **Auto-sync** when connection resumes
   - Background Sync API posts updates to `/api/resource/Trips/{id}`
   - Last-write-wins conflict resolution (naive, acceptable for field app)

**Phase 2 (With custom app) — Enhanced Offline + Custom Sync:**

1. Create custom app endpoint `/api/method/roqson_core.sync.bulk_push`
   - Implements server-side conflict resolution
   - Handles complex sync scenarios

2. Install [PWA Frappe marketplace app](https://cloud.frappe.io/marketplace/apps/pwa_frappe)
   - Automates service worker + manifest config

3. Serve full PWA from custom app route (not just Frappe Page)
   - Asset bundling, proper SPA framework (Vue/React)

**Timeline:**
- Phase 1: 2–3 weeks (no blocker, start today)
- Phase 2: 1–2 weeks (after custom app is stable)

---

### Recommended Sequence (6-Month Plan)

#### **Month 1: Plan & Validate**
- [ ] Confirm Frappe Cloud tier (Private Bench vs. Shared Hosting)
- [ ] Set up staging bench (restore production backup to test)
- [ ] Snapshot all 117 Server Scripts locally (git check-in)
- [ ] Document all custom field changes made via UI (create audit spreadsheet)
- [ ] Choose git hosting (GitHub, GitLab)

#### **Month 2: Build Phase 1 Custom App (Low Risk)**
- [ ] Create `roqson_core` Frappe app skeleton
- [ ] Move all 28 active API Server Scripts → `roqson_core/api.py`
- [ ] Migrate custom fields → fixtures
- [ ] Migrate print formats → fixtures
- [ ] Test on staging bench (install, run tests, verify API endpoints still work)
- [ ] Deploy to production

#### **Month 3: Start Building Trip Ticket PWA**
- [ ] Create Frappe Page for PWA UI (or external domain + CORS config)
- [ ] Implement token auth + IndexedDB caching
- [ ] Build delivery form UI (Trips list, order details, status update)
- [ ] Test offline mode with IndexedDB mock data
- [ ] Deploy Phase 1 PWA

#### **Month 4–5: Advance App & Offline Sync**
- [ ] Move DocType Event Server Scripts → app hooks (start with low-risk doctype, e.g., Receipt)
- [ ] Phase 2 custom sync endpoints (bulk upsert, conflict resolution)
- [ ] Install PWA Frappe marketplace app
- [ ] Integrate background sync API
- [ ] Test on staging with production data

#### **Month 6: DocType & Workflow Migration (High Risk) + Production PWA**
- [ ] Migrate remaining Server Scripts → app (full audit + testing)
- [ ] Export DocType fixtures (test on staging first)
- [ ] Export Workflow fixtures (test on staging)
- [ ] Final production deploy + PWA rollout

---

## Checklist: Before You Start

### Immediate (This Week)
- [ ] **Confirm Frappe Cloud tier**: Log in to dashboard, verify Private Bench availability
- [ ] **Confirm API credentials work**: Test `roqson.py` can authenticate
- [ ] **Create git org/repo**: Set up GitHub org for `roqson_core` app
- [ ] **Backup production**: Manual backup via Frappe Cloud dashboard (Backups tab)

### Pre-Phase 1 (Next 2 Weeks)
- [ ] **Create staging bench**: Restore production database to a staging site
- [ ] **Snapshot all scripts**: Run `python -c "import roqson; roqson.snapshot_scripts('Server Script')"` for each DocType
- [ ] **Audit disabled scripts**: List all `enabled=0` Client Scripts (don't migrate these)
- [ ] **Validate custom field list**: Run SQL query against live DB, compare to audit

### Phase 1 (Month 2)
- [ ] **Scaffold app**: `frappe new-app roqson_core` locally
- [ ] **Port API scripts**: Move 28 active APIs to `api.py`
- [ ] **Export fixtures**: Custom fields + print formats
- [ ] **Write README**: Installation steps, API endpoint docs
- [ ] **Test on staging**: `bench --site staging.local install-app roqson_core`
- [ ] **Verify all APIs work**: Run test requests against each endpoint
- [ ] **Deploy to production**: Install via Frappe Cloud dashboard

---

## Reference: Key Frappe Cloud Documentation

- **Custom App Installation**: [Frappe Cloud custom app docs](https://docs.frappe.io/cloud/benches/custom-app)
- **Site Backup & Restore**: [Frappe Cloud restore docs](https://docs.frappe.io/cloud/sites/migrate-an-existing-site)
- **Server Scripts**: [Frappe v15 Server Script docs](https://docs.frappe.io/framework/v15/user/en/desk/scripting/server-script)
- **REST API**: [Frappe v15 REST API docs](https://docs.frappe.io/framework/v15/user/en/api/rest)
- **Token Auth**: [Frappe token auth docs](https://docs.frappe.io/framework/v15/user/en/guides/integration/how_to_setup_token_based_auth)
- **PWA Frappe App**: [PWA Frappe marketplace](https://cloud.frappe.io/marketplace/apps/pwa_frappe)
- **Workflows**: [Frappe Workflow documentation](https://docs.frappe.io/framework/v15/user/en/desk/workflows/workflow)

---

## Conclusion

**A custom app migration is feasible and worthwhile, but only with a phased approach:**

1. **Phase 1** (2–4 weeks) — Low-risk API scripts + fixtures → gain version control + proper Python
2. **Phase 2** (2–4 weeks) — Build offline-capable Trip Ticket PWA alongside app development
3. **Phase 3** (4–8 weeks, staged rollout) — Migrate DocTypes + Workflows only after staging validation

**Do NOT attempt to migrate everything at once.** The risks (fixture conflicts, workflow orphaning, data loss) are manageable only if you proceed incrementally with staging validation at each step.

**Before any Phase 2 install:** Confirm your Frappe Cloud plan is **Private Bench** (not Shared Hosting), and take a manual backup.

---

**Report Generated**: 2026-03-15
**Analysis Date**: 2026-03-15
**Live Audit from**: roqson-industrial-sales.s.frappe.cloud
