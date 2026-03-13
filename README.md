# ROQSON Agentic Dev

Automated management and deployment repository for the **ROQSON Industrial Sales** ERPNext instance. This repository contains the tools, scripts, and automation logic used to maintain an automotive lubricant ERP solution on Frappe Cloud.

## 🚀 Project Essence
- **Goal**: Capstone Thesis project providing a custom ERP solution for ROQSON.
- **Environment**: Managed Frappe Cloud (REST API-based management).
- **Core Tool**: `roqson.py` — A specialized REST API wrapper for Frappe/ERPNext.

## 🛠 Technical Stack
- **Platform**: Frappe / ERPNext v15.x
- **Scripting**: Python (Server Scripts) & JavaScript (Client Scripts).
- **Architecture**: Event-driven automation using `RestrictedPython` on the server side.

## 📁 Key Components
- **`roqson.py`**: The primary interface for interacting with the Frappe API. Includes safe script deployment with diff verification.
- **`scripts/`**: Collection of production server and client scripts.
- **`schema_check.py`**: Data integrity tool for validating document statuses against workflow schemas.
- **Order & Delivery Flow**: Automated transitions between `Draft`, `Needs Review`, `Approved`, and `In Transit`.

## 🤖 Agent Operating Procedure
This repository is designed to be managed by AI agents (Gemini CLI, Claude Code).
1. **Research**: Fetch logs and current scripts using `roqson.py`.
2. **Strategy**: Propose minimal, targeted fixes with diff previews.
3. **Execution**: Safe deployment using `update_doc` with f-string and `.format()` safety checks for Server Scripts.

## ⚠️ Critical Safety Rules
- **Read-Before-Write**: Never overwrite scripts without fetching the current state first.
- **Soft-Disable**: Set `enabled: 0` or `disabled: 1` instead of deleting scripts.
- **RestrictedPython**: Server scripts must use string concatenation (`+`) instead of f-strings or `.format()`.
- **Workflow Integrity**: Always use workflow actions or established hooks to update statuses.

---
*Developed as part of the ROQSON Industrial Sales Capstone.*
