"""
roqson.py — ROQSON ERPNext API Wrapper
Read-before-write pattern enforced for all script operations.
Credentials loaded from ROQSON_API_KEY and ROQSON_API_SECRET env vars.
"""

import os
import json
import requests
from datetime import datetime
from difflib import unified_diff
from dotenv import load_dotenv

# Load credentials from .env if present
load_dotenv(override=True)

# ── Auth ──────────────────────────────────────────────────────────────────────

BASE = "https://roqson-industrial-sales.s.frappe.cloud"

def _auth():
    key = os.environ.get("ROQSON_API_KEY")
    secret = os.environ.get("ROQSON_API_SECRET")
    if not key or not secret:
        raise EnvironmentError(
            "ROQSON_API_KEY and ROQSON_API_SECRET must be set as environment variables."
        )
    return (key, secret)

def _headers():
    key, secret = _auth()
    return {"Authorization": f"token {key}:{secret}"}

# ── Core CRUD ─────────────────────────────────────────────────────────────────

def get_doc(doctype: str, name: str) -> dict:
    """Fetch a single document with all fields."""
    url = f"{BASE}/api/resource/{doctype}/{name}"
    r = requests.get(url, headers=_headers())
    r.raise_for_status()
    return r.json()["data"]


def list_docs(doctype: str, fields: list, filters: list = None, limit: int = 100) -> list:
    """List documents with specified fields and optional filters."""
    params = {
        "fields": json.dumps(fields),
        "limit_page_length": limit,
        "order_by": "modified desc"
    }
    if filters:
        params["filters"] = json.dumps(filters)
    r = requests.get(f"{BASE}/api/resource/{doctype}", params=params, headers=_headers())
    r.raise_for_status()
    return r.json().get("data", [])


def update_doc(doctype: str, name: str, data: dict) -> dict:
    """Partial update of a document. Returns updated document."""
    r = requests.put(
        f"{BASE}/api/resource/{doctype}/{name}",
        json=data,
        headers=_headers()
    )
    r.raise_for_status()
    return r.json()["data"]


def call_method(method: str, **kwargs) -> dict:
    """Call a Frappe whitelisted method or API-type Server Script."""
    r = requests.post(
        f"{BASE}/api/method/{method}",
        json=kwargs,
        headers=_headers()
    )
    r.raise_for_status()
    return r.json()

# ── Error Logs ────────────────────────────────────────────────────────────────

def get_error_logs(limit: int = 20) -> list:
    """Fetch recent error logs ordered by newest first."""
    return list_docs(
        "Error Log",
        fields=["name", "method", "error", "creation"],
        limit=limit
    )


def print_error_logs(limit: int = 20):
    """Pretty-print recent error logs for inspection."""
    logs = get_error_logs(limit)
    print(f"\n{'─'*60}")
    print(f"  Recent Error Logs ({len(logs)} entries)")
    print(f"{'─'*60}")
    for log in logs:
        print(f"\n[{log.get('creation', 'unknown time')}]")
        print(f"  Method : {log.get('method', 'N/A')}")
        error_preview = (log.get('error') or '')[:300].replace('\n', ' ')
        print(f"  Error  : {error_preview}...")
    print(f"{'─'*60}\n")

# ── Script Operations ─────────────────────────────────────────────────────────

def get_scripts_for_doctype(doctype: str) -> dict:
    """
    Fetch all Client Scripts and Server Scripts associated with a doctype.
    Returns: { "client": [...], "server": [...] }
    """
    client = list_docs(
        "Client Script",
        fields=["name", "dt", "enabled", "script", "modified"],
        filters=[["dt", "=", doctype]],
        limit=200
    )
    server = list_docs(
        "Server Script",
        fields=["name", "script_type", "reference_doctype", "script", "disabled", "modified"],
        filters=[["reference_doctype", "=", doctype]],
        limit=200
    )
    print(f"\nFound {len(client)} Client Script(s) and {len(server)} Server Script(s) for '{doctype}'")
    return {"client": client, "server": server}


def get_script_body(doctype: str, name: str) -> str:
    """
    Fetch the script body of a Client Script or Server Script.
    doctype: 'Client Script' or 'Server Script'
    """
    doc = get_doc(doctype, name)
    return doc.get("script", "")


def _show_diff(old: str, new: str, name: str):
    """Print a unified diff between old and new script content."""
    old_lines = old.splitlines(keepends=True)
    new_lines = new.splitlines(keepends=True)
    diff = list(unified_diff(old_lines, new_lines, fromfile=f"{name} (current)", tofile=f"{name} (proposed)"))
    if diff:
        print(f"\n{'─'*60}")
        print(f"  Proposed changes to: {name}")
        print(f"{'─'*60}")
        print("".join(diff))
        print(f"{'─'*60}\n")
    else:
        print(f"\n[No changes detected in {name}]\n")


def safe_update_script(doctype: str, name: str, new_script: str, auto_confirm: bool = False) -> dict | None:
    """
    Read-before-write script update with diff preview and confirmation.

    Steps:
    1. Fetch current script
    2. Show unified diff
    3. Ask for confirmation (unless auto_confirm=True)
    4. Write update
    5. Re-fetch to verify

    Returns updated document or None if cancelled.
    """
    print(f"\n[READ] Fetching current script: {doctype} / {name}")
    current = get_script_body(doctype, name)

    _show_diff(current, new_script, name)

    if current.strip() == new_script.strip():
        print("[SKIP] No changes to apply.")
        return None

    if not auto_confirm:
        confirm = input(f"Apply this change to '{name}'? [y/N]: ").strip().lower()
        if confirm != "y":
            print("[CANCELLED] No changes written.")
            return None

    print(f"[WRITE] Updating {doctype} / {name}...")
    update_doc(doctype, name, {"script": new_script})

    print(f"[VERIFY] Re-fetching to confirm...")
    verified = get_script_body(doctype, name)
    if verified.strip() == new_script.strip():
        print(f"[OK] '{name}' updated successfully.")
    else:
        print(f"[WARNING] Verification mismatch — check the script manually.")

    return get_doc(doctype, name)


def disable_script(doctype: str, name: str):
    """
    Safely disable a script without deleting it.
    Use this instead of deletion when a script is causing problems.
    """
    if doctype == "Client Script":
        update_doc(doctype, name, {"enabled": 0})
    elif doctype == "Server Script":
        update_doc(doctype, name, {"disabled": 1})
    print(f"[DISABLED] {doctype} / {name}")

# ── Investigation Helpers ─────────────────────────────────────────────────────

def investigate(doctype: str = None, error_limit: int = 20):
    """
    Full investigation entry point.
    Fetches error logs and (optionally) all scripts for a doctype.
    Use this as the first call when starting a new ticket.
    """
    print_error_logs(error_limit)
    if doctype:
        return get_scripts_for_doctype(doctype)


def find_scripts_by_keyword(keyword: str) -> dict:
    """
    Search all Client and Server Scripts by name keyword.
    Useful when you know part of the script name but not the exact doctype.
    """
    keyword_lower = keyword.lower()

    all_client = list_docs(
        "Client Script",
        fields=["name", "dt", "enabled", "modified"],
        limit=200
    )
    all_server = list_docs(
        "Server Script",
        fields=["name", "script_type", "reference_doctype", "disabled", "modified"],
        limit=200
    )

    matched_client = [s for s in all_client if keyword_lower in s["name"].lower()]
    matched_server = [s for s in all_server if keyword_lower in s["name"].lower()]

    print(f"\nSearch results for '{keyword}':")
    print(f"  Client Scripts: {len(matched_client)}")
    for s in matched_client:
        status = "enabled" if s.get("enabled") else "disabled"
        print(f"    [{status}] {s['name']} → {s['dt']}")
    print(f"  Server Scripts: {len(matched_server)}")
    for s in matched_server:
        status = "disabled" if s.get("disabled") else "active"
        print(f"    [{status}] {s['name']} ({s['script_type']}) → {s.get('reference_doctype', 'none')}")

    return {"client": matched_client, "server": matched_server}


def snapshot_scripts(doctype: str, output_file: str = None):
    """
    Export all scripts for a doctype to a JSON file for backup/review.
    Useful before making changes to a heavily-scripted doctype like Order Form.
    """
    scripts = get_scripts_for_doctype(doctype)

    # Fetch full bodies
    for s in scripts["client"]:
        s["script"] = get_script_body("Client Script", s["name"])
    for s in scripts["server"]:
        s["script"] = get_script_body("Server Script", s["name"])

    if not output_file:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = f"snapshot_{doctype.replace(' ', '_')}_{timestamp}.json"

    with open(output_file, "w") as f:
        json.dump(scripts, f, indent=2)

    print(f"[SNAPSHOT] Saved {len(scripts['client'])} client + {len(scripts['server'])} server scripts to {output_file}")
    return output_file


# ── Quick Reference ───────────────────────────────────────────────────────────

CUSTOM_DOCTYPES = [
    "Order Form", "Order Details Table", "Order Summary Table",
    "Order - VAT Table", "Order- Pricing Table", "Applied Promos Table",
    "Trip Ticket", "Trip Ticket Table",
    "Customer Information", "Customer Information Outlet Address",
    "Customer Survey Form", "Credit Application", "Credit Application Request",
    "Product", "Product Bundles", "Products Price list",
    "Discounts", "Promos", "Brands",
    "Vehicles", "Warehouses", "Territories",
    "Sales Personnel", "Nature of Business",
    "Inventory Ledger", "Inventory Balance",
    "PH Address", "PH Province", "PH City Municipality", "PH Barangay",
]

API_SCRIPTS = {
    "get_product_stock_api": "Stock availability check",
    "eligible_orders_by_outlet": "Trip Ticket order filtering",
    "get_active_trip_order_names": "Active order lookup",
    "get_customer_orders": "Customer order history",
    "rpm_get_fields": "Field permission manager",
    "rpm_get_roles": "Role listing",
    "rpm_update_permission": "Permission updates",
    "fix_credit_app": "Credit application utility",
    "timestamping": "Trip Ticket server time stamp",
}

ORDER_FORM_WORKFLOW_STATES = [
    "Draft", "Submitted", "Approved", "Reserved",
    "Dispatched", "Delivered", "Delivery Failed", "Rescheduled"
]


if __name__ == "__main__":
    # Quick sanity check — run with: python roqson.py
    print("ROQSON API Wrapper — connection test")
    try:
        logs = get_error_logs(limit=3)
        print(f"[OK] Connected. Found {len(logs)} recent error log entries.")
    except Exception as e:
        print(f"[FAIL] {e}")
