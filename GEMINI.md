# ROQSON ERPNext — Project Context & Guide

This document is the foundational context for any agent (Claude Code, Gemini CLI, Codex) working on the ROQSON Industrial Sales ERPNext instance.

---

## Project Essence
- **Goal**: Automotive lubricant ERP solution for ROQSON (Capstone Thesis).
- **Environment**: Managed Frappe Cloud (No SSH/Bench access).
- **Primary Tool**: `roqson.py` (REST API Wrapper).
- **Workflow State**: The project uses Workflows for Order Form and Trip Ticket. Statuses are automated via Server Scripts.

---

## Technical Stack & Constraints

| Property | Value |
|---|---|
| **Base URL** | `https://roqson-industrial-sales.s.frappe.cloud` |
| **Frappe/ERPNext** | v15.x |
| **Auth** | API key + secret via `Authorization: token {key}:{secret}` |
| **Server Scripts** | RestrictedPython (safe_exec). **NO f-strings, NO .format()**. Use string concatenation (`+`) and `str()`. |
| **Scripting** | Heavy reliance on Client Scripts (JS) and Server Scripts (Python). |

---

## Core Operational Flow

### 1. Order Flow
`Draft → Needs Review → Approved`
- **Approval**: Auto-creates a **Sales** record in `Pending` status.
- **Cancellation**: Bidirectional. Cancelling an Order cancels the Sale, and vice versa (with user confirmation).

### 2. Delivery & Trip Tickets
- **Trip Ticket**: Used to bundle Sales for delivery.
- **Workflow (Time in Time out)**: `Draft → In Transit → Arrived → Delivered`.
- **Status Automation**:
  - `Save Trip Ticket` → Sales status: `Dispatching`.
  - `Dispatch Action` → Sales status: `In Transit`.
  - `Delivery Status (Successful)` → Sales status: `Received`.
  - `Delivery Status (Failed)` → Sales status: `Failed`.
- **Pick-up**: Skips Trip Ticket. Marked `Received` via "Confirm Pick-up" button on Sales Form.

---

## Agent Operating Procedure

### Phase 1: Research (Fetch First)
1. **Check Error Logs**: `python -c "import roqson; roqson.print_error_logs(20)"`.
2. **Identify Scripts**: Search for DocType-specific scripts: `python -c "import roqson; roqson.get_scripts_for_doctype('Doctype Name')"`.
3. **Read Current Code**: Always read the existing script before proposing changes.

### Phase 2: Strategy
- Explain the root cause in plain English.
- Propose a minimal fix.
- **Show a diff** and wait for user confirmation.

### Phase 3: Execution & Validation
- **Deploy**: Use `roqson.update_doc` for scripts.
- **Permission Query Test**: If updating a Permission Query, test via `/api/method/frappe.desk.reportview.get`.
- **Sandbox Validation**: Ensure no `.format()` or f-strings in Server Scripts.

---

## Critical Safety Rules (Non-Negotiable)

1. **Read-Before-Write**: Never overwrite a script without reading its current state.
2. **Soft-Disable**: Never delete a script. Set `enabled: 0` (Client) or `disabled: 1` (Server).
3. **Workflow Integrity**: Never set `docstatus` or `status` directly on workflow-controlled docs; use workflow actions or existing automation hooks.
4. **Minimal Blast Radius**: Fix the specific issue without refactoring unrelated code.
5. **No Secrets**: Never print or log `ROQSON_API_SECRET`.

---

## Naming & Conventions
- **Client Scripts**: `{Doctype}: {Description}`
- **Server Scripts**: `{Description} (API/DocType Event)`
- **Archive Logic**: `Archive {Doctype}` (implements soft-delete). Do not modify unless asked.
- **RPM**: `RPM {Name}` (Role/Permission subsystem). Treat with extreme care.

---

## Script Inventory (Key Doctypes)
- **Order Form**: ~40 Client Scripts. Interdependent pricing and stock logic.
- **Sales**: Status automation and pick-up handling.
- **Trip Ticket**: Dispatch workflow and delivery outcomes.
