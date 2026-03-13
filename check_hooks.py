import roqson
import json

scripts = roqson.list_docs("Client Script", fields=["name", "script", "enabled"], filters={"dt": "Order Form", "enabled": 1}, limit=200)

for s in scripts:
    script_content = s.get("script", "")
    if "before_workflow_action" in script_content:
        print(f"\n--- MATCH IN: {s['name']} ---")
        lines = script_content.split("\n")
        for i, line in enumerate(lines):
            if "before_workflow_action" in line:
                print(f"  Line {i+1}: {line.strip()}")
