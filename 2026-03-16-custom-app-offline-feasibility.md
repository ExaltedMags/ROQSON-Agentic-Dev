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
- 6-month phased migration plan with checklists

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

### Hosting Tier — UNCONFIRMED
**Critical unresolved item**: Whether the current $25/mo Frappe Cloud plan is:
- **Shared Hosting** → no custom app install possible
- **Private Bench** → custom app install via dashboard UI

The entire Phase 1 plan (custom app) depends on this being a Private Bench. **Must verify in Frappe Cloud dashboard before proceeding.**

### Frappe-Specific Gotchas Discovered
1. **Fixture `modified` timestamp**: Fixtures are silently skipped if their `modified` field ≤ DB record's `modified`. Always bump to current datetime ISO before any fixture install.
2. **RestrictedPython scope**: Generator expressions cannot close over outer-scope variables in Server Scripts. Existing workarounds (for-loops) are already in place — don't break them during migration.
3. **`Trips` DocType name**: Internal name is `Trips`, not `Trip Ticket`. All API calls and scripts use `Trips`.

---

## Immediate Next Steps (Priority Order)

1. **Verify Frappe Cloud hosting tier** (5 min)
   - Log into Frappe Cloud dashboard
   - Check if you see a "Bench" sidebar item with an "Apps" tab that allows adding from GitHub
   - If yes → Private Bench, Phase 1 is unblocked
   - If no → must upgrade tier before any custom app work

2. **Review `FEASIBILITY_ANALYSIS.md`** for stakeholder sign-off
   - Particularly the "Recommendation" and "Recommended Sequence" sections
   - Confirm 6-month phased approach is acceptable scope

3. **If Phase 1 approved — start scaffold**:
   - Create GitHub repo for `roqson_core` app
   - Run `frappe new-app roqson_core` locally (requires Frappe bench installed locally for scaffolding only)
   - OR: use the [Frappe app template](https://github.com/frappe/frappe_app_template) on GitHub to create the skeleton without a local bench

4. **If offline PWA approved — start immediately** (no custom app required):
   - Create a Frappe Page DocType via web UI
   - Build HTML/JS Trip Ticket companion app
   - Use existing `roqson.py` auth pattern (token header) for API calls
   - IndexedDB + service worker for offline caching

---

## Decisions Made

| Decision | Rationale |
|---|---|
| **Don't migrate all 59 DocTypes at once** | Fixture conflicts, workflow orphaning, data loss risk too high. Phase in low-risk items first. |
| **Migrate API Server Scripts first** (Phase 1) | Lowest risk (stateless, no events, easy to test). Biggest gain (proper Python, imports, f-strings). |
| **Leave Workflows alone until staging bench** | 4 active workflows have production documents. Orphaned workflow states are hard to recover from. |
| **Start PWA as Frappe Page (no custom app)** | Eliminates CORS, no hosting tier dependency, can start immediately. Upgrade to proper SPA later. |
| **Report confirmed CORS requires config** | Cross-origin PWA will hit CORS errors on Authorization header requests. Same-origin via Frappe Page avoids this entirely. |

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

### RestrictedPython Rules (Server Scripts)
- No f-strings → use string concatenation
- No `.format()` → use `+` and `str()`
- Generators can't close over outer-scope vars → use `for` loops
- Only `json` is importable in the sandbox
- API scripts return via `frappe.response['message'] = ...`

---

## Potential Gotchas for Next Session

1. **Fixture silent skip**: If you try to install a fixture and nothing changes, check the `modified` timestamp. Bump it to current datetime.
2. **Client Script endpoint paths**: If you migrate API Server Scripts to app Python, ALL Client Scripts referencing those endpoints will break unless you update their `/api/method/` calls in sync.
3. **`Trips` vs `Trip Ticket`**: The Frappe Cloud DocType name is `Trips`. The Server Script `reference_doctype` is also `Trips`. The CLAUDE.md and roqson.py `CUSTOM_DOCTYPES` list uses "Trip Ticket" — this is a naming inconsistency that existed before this session.
4. **Disabled scripts**: ~50+ Client Scripts and ~30 Server Scripts are disabled. Do NOT migrate disabled scripts — they are dead code.
5. **Private Bench dependency**: The entire custom app Phase 1 is blocked if hosting is Shared Hosting. Check this first.

---

## What Was NOT Done (Out of Scope)

- No scripts were modified or deployed
- No DocTypes were changed
- No migration was started
- No custom app was created
- The feasibility analysis is purely advisory — no changes to the live instance

---

## Research Sources Used

- Live Frappe REST API calls to `roqson-industrial-sales.s.frappe.cloud`
- Frappe v15 documentation (Server Scripts, REST API, Token Auth, Workflows)
- Frappe Cloud documentation (Custom App Install, Site Restore)
- Frappe GitHub issues (#19655 re: fixture migration, #36398 re: DocType fixtures)
- Frappe Discuss forum (Permission Query, CORS, safe_exec restrictions)
- Background research agent findings (confirmed and cross-checked all key points)

---

## Pending Work

- [ ] Confirm Frappe Cloud hosting tier (Private Bench vs Shared Hosting)
- [ ] Review + approve `FEASIBILITY_ANALYSIS.md` with stakeholders
- [ ] Decide: proceed with Phase 1 custom app, or Phase 0 offline PWA (or both in parallel)
- [ ] If Phase 1: create GitHub repo, scaffold `roqson_core` app skeleton
- [ ] If PWA: create Frappe Page DocType for Trip Ticket companion app

---

**Handoff Quality**: High — entire session was research/documentation with no partial code changes. Next agent can pick up any of the "Immediate Next Steps" without needing further context from this session.
