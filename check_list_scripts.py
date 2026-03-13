import roqson

scripts = roqson.list_docs("Client Script", fields=["name", "script", "enabled", "view"], filters={"dt": "Order Form", "enabled": 1}, limit=200)

print("Enabled Client Scripts for Order Form (List View):")
found_list = False
for s in scripts:
    if s.get("view") == "List":
        found_list = True
        print(f"\n--- {s['name']} ---")
        lines = s.get("script", "").split("\n")
        for i, line in enumerate(lines):
            if i < 15 or "workflow" in line.lower() or "action" in line.lower():
                print(f"  Line {i+1}: {line.strip()}")

if not found_list:
    print("No List view scripts found.")
