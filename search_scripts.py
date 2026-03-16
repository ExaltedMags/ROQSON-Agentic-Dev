import roqson
import json

scripts = roqson.list_docs("Client Script", fields=["name", "script", "enabled"], filters={"dt": "Order Form", "enabled": 1}, limit=200)

for s in scripts:
    script_content = s.get("script", "")
    if "Reserve Stock" in script_content or "Reserve" in script_content or "warehouse" in script_content.lower():
        print(f"\n--- MATCH IN: {s['name']} ---")
        lines = script_content.split("\n")
        for i, line in enumerate(lines):
            if "Reserve Stock" in line or "frappe.prompt" in line or "warehouse" in line.lower() or "workflow_state" in line:
                print(f"  Line {i+1}: {line.strip()}")
