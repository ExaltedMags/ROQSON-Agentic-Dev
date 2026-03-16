# Handoff: Custom App Migration & Offline PWA Feasibility Analysis

**Created**: 2026-03-16
**Project**: D:\claude roqson (ROQSON ERPNext)
**Git**: Not a git repository
**Session Type**: Research & Documentation (no code changes made)

---

## Current State Summary

A full feasibility analysis was completed and exported. The session covered two distinct questions:
1. Whether to migrate from UI-based ERPNext customizations to a proper custom Frappe app
2. Whether an offline-capable field app (PWA) is feasible given the current hosting setup

**All work is complete for this session.** No scripts were modified. No DocTypes were changed. The only output was a documentation file.

The migration has been approved by the team. A development freeze is in effect — no changes to the live ERPNext instance until migration is complete and stable.

---

## Work Completed This Session

### Live Audit Performed
Used the Frappe REST API (via `roqson.py`) to fetch and summarize the current customization surface:

| Item | Count |
|---|---|
| Custom DocTypes | 59 |
| Server Scripts (total) | 117 (active: ~75) |
| Client Scripts (total) | 190 (active: ~106) |
| Active Workflows | 4 |
| Custom Fields | 44 |
| Custom Print Formats | 2 |

### Output File Created
**`D:\claude roqson\FEASIBILITY_ANALYSIS.md`** — comprehensive report covering:
- Full audit tables with all customization types
- Per-type migration risk assessment (Low/Medium/High)
- Fixture conflict deep-dive (critical `modified` timestamp gotcha)
- Server script sandbox changes when moved to app Python
- Workflow state orphaning risk + safe migration path
- Data continuity analysis for production DocTypes
- Frappe Cloud rollback procedures
- Offline PWA feasibility verdict + architecture
- Phased migration plan with checklists

---

## Important Context

### Live Instance Details
- **URL**: `https://roqson-industrial-sales.s.frappe.cloud`
- **Auth**: `ROQSON_API_KEY` + `ROQSON_API_SECRET` from `.env` file
- **Wrapper**: `D:\claude roqson\roqson.py`
- **Frappe version**: v15.x
- **No SSH/bench access** — all work done via REST API and web UI

### Key DocType Names (UI names differ from internal)
- **"Trip Ticket"** in docs/comments = `Trips` in the live database (DocType name)
- This matters: server scripts reference `reference_doctype = "Trips"`, not "Trip Ticket"

### Hosting Tier — CONFIRMED ✅
The site is on **ROQSON-private-bench**, $25/mo plan. Custom app installation via the Frappe Cloud dashboard is supported. This is unblocked — no upgrade needed.

### Frappe-Specific Gotchas Discovered
1. **Fixture `modified` timestamp**: Fixtures are silently skipped if their `modified` field ≤ DB record's `modified`. Always bump to current datetime ISO before any fixture install.
2. **RestrictedPython scope**: Generator expressions cannot close over outer-scope variables in Server Scripts. Existing workarounds (for-loops) are already in place — don't break them during migration.
3. **`Trips` DocType name**: Internal name is `Trips`, not `Trip Ticket`. All API calls and scripts use `Trips`.

---

## Immediate Next Steps (Priority Order)

1. **Scaffold `roqson_core` app** — create a private GitHub repo, then either:
   - Run `frappe new-app roqson_core` locally (requires local bench), OR
   - Use the [Frappe app template](https://github.com/frappe/frappe_app_template) on GitHub to create the skeleton without a local bench
   - Push the skeleton to the GitHub repo

2. **Create staging site on Frappe Cloud** — restore from the latest production backup via the Frappe Cloud dashboard. All phase testing happens here before touching production.

3. **Phase 1 migration (low risk)** — port all active API Server Scripts to `roqson_core/api.py`. Export Custom Fields and Print Formats as fixtures. Test on staging, then deploy. Update all Client Scripts referencing old API paths in the same deployment window.

4. **Phase 2 migration (medium risk)** — DocType event scripts move into the app, one DocType at a time. Start with the simplest (Receipt) and end with the most complex (Order Form, Trips).

5. **Phase 3 migration (high risk)** — DocType and Workflow fixtures. Only after Phase 2 is stable and staging validation passes. Zero changes to workflow state names — orphaning is hard to recover from.

6. **Bug resolution** — fix anything the migration broke. Development freeze lifts after this step.

> **At each phase boundary:** staging test → manual backup → production deploy → verify.

---

## Decisions Made

| Decision | Rationale |
|---|---|
| **Migration approved, development freeze in effect** | All changes to the live ERPNext instance are paused until migration is complete and stable. |
| **Don't migrate all 59 DocTypes at once** | Fixture conflicts, workflow orphaning, data loss risk too high. Phase in low-risk items first. |
| **Migrate API Server Scripts first** (Phase 1) | Lowest risk (stateless, no events, easy to test). Biggest gain (proper Python, imports, f-strings). |
| **Leave Workflows alone until staging bench** | 4 active workflows have production documents. Orphaned workflow states are hard to recover from. |
| **Offline features are post-migration** | Offline work starts only after the system is confirmed stable on `roqson_core`. Not a parallel track. |
| **Start PWA as Frappe Page if needed pre-migration** | Eliminates CORS, no hosting tier dependency. Upgrade to proper SPA after migration if required. |
| **CORS requires config for cross-origin PWA** | Cross-origin PWA will hit CORS errors on Authorization header requests. Same-origin via Frappe Page avoids this entirely. |

---

## Critical Files

| File | Purpose |
|---|---|
| `D:\claude roqson\roqson.py` | REST API wrapper — all API interactions go through here |
| `D:\claude roqson\.env` | API credentials (never log these) |
| `D:\claude roqson\FEASIBILITY_ANALYSIS.md` | Full output from this session |
| `D:\claude roqson\CLAUDE.md` | Project context and operating procedures for agents |

---

## Key Patterns Discovered

### roqson.py Usage
```python
import roqson

# List with filters
docs = roqson.list_docs('Server Script', ['name','script_type','reference_doctype','disabled'], limit=150)

# Fetch single doc
doc = roqson.get_doc('Server Script', 'Script Name Here')

# Safe script update (shows diff, asks confirmation)
roqson.safe_update_script('Server Script', 'Script Name', new_code)
```

### RestrictedPython Rules (Server Scripts — current state, pre-migration)
- No f-strings → use string concatenation
- No `.format()` → use `+` and `str()`
- Generators can't close over outer-scope vars → use `for` loops
- Only `json` is importable in the sandbox
- API scripts return via `frappe.response['message'] = ...`

### App Python Rules (post-migration — restrictions lifted)
- f-strings work
- `import` works — full stdlib and third-party packages available
- Generators and comprehensions work normally
- Doc event handlers: `def before_save(doc, method):` pattern
- API endpoints: `@frappe.whitelist()` decorator on functions in `api.py`
- Endpoint path changes from `frappe.handler.run_server_script` to `roqson_core.api.<function_name>`

---

## Potential Gotchas for Next Session

1. **Fixture silent skip**: If you install a fixture and nothing changes, check the `modified` timestamp. Bump it to current datetime ISO format.
2. **Client Script endpoint paths**: Migrating API Server Scripts to app Python changes all `/api/method/` paths. ALL Client Scripts referencing those endpoints break unless updated in the same deployment window.
3. **`Trips` vs `Trip Ticket`**: The Frappe Cloud DocType name is `Trips`. The Server Script `reference_doctype` is also `Trips`. The CLAUDE.md and roqson.py `CUSTOM_DOCTYPES` list uses "Trip Ticket" — this naming inconsistency existed before this session.
4. **Disabled scripts**: ~50+ Client Scripts and ~30 Server Scripts are disabled. Do NOT migrate disabled scripts — they are dead code.
5. **Workflow state names**: Do not rename any workflow state during the migration. Even a capitalization change will orphan existing documents, which requires manual SQL recovery.
6. **Manual backup before every production deploy**: Frappe Cloud auto-backups are daily. If a deploy breaks something on day 1, the latest auto-backup is from day 0 — you lose a day of data. Always take a manual backup immediately before each phase deploy.

---

## What Was NOT Done (Out of Scope This Session)

- No scripts were modified or deployed
- No DocTypes were changed
- No migration was started
- No custom app was created
- The feasibility analysis is purely advisory — no changes to the live instance

---

## Pending Work

- [ ] Scaffold `roqson_core` app skeleton (GitHub repo + `frappe new-app` or template)
- [ ] Create staging site from production backup on Frappe Cloud
- [ ] Phase 1: Audit and list all active API Server Scripts to port
- [ ] Phase 1: Port API scripts → `roqson_core/api.py`
- [ ] Phase 1: Export Custom Fields as fixtures
- [ ] Phase 1: Export Print Formats as fixtures
- [ ] Phase 1: Update all Client Scripts referencing old API paths
- [ ] Phase 1: Staging test → backup → production deploy → verify
- [ ] Phase 2: Port DocType event scripts (Receipt → Customer Info → Credit App → Sales → Trips → Order Form)
- [ ] Phase 2: Staging test → backup → production deploy → verify per DocType
- [ ] Phase 3: DocType fixtures (staging validation required, zero field renames)
- [ ] Phase 3: Workflow fixtures (zero state name changes, staging test first)
- [ ] Phase 3: Production deploy → verify all workflow states intact on existing documents
- [ ] Bug resolution → lift development freeze

---

## Research Sources Used

- Live Frappe REST API calls to `roqson-industrial-sales.s.frappe.cloud`
- Frappe v15 documentation (Server Scripts, REST API, Token Auth, Workflows)
- Frappe Cloud documentation (Custom App Install, Site Restore)
- Frappe GitHub issues (#19655 re: fixture migration, #36398 re: DocType fixtures)
- Frappe Discuss forum (Permission Query, CORS, safe_exec restrictions)
- Background research agent findings (confirmed and cross-checked all key points)

---

**Handoff Quality**: High — entire session was research/documentation with no partial code changes. Next agent can pick up directly from "Immediate Next Steps" step 1 without needing further context from this session.
