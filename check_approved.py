import roqson

print("--- Recent Error Logs ---")
try:
    roqson.print_error_logs(limit=3)
except Exception as e:
    print(f"Error getting logs: {e}")

print("\n--- Checking Server Scripts for 'Approved' ---")
scripts = roqson.list_docs("Server Script", fields=["name", "script", "disabled"], filters={"reference_doctype": "Order Form", "disabled": 0}, limit=200)

for s in scripts:
    script_content = s.get("script", "")
    if "\"Approved\"" in script_content or "'Approved'" in script_content:
        print(f"MATCH IN: {s['name']}")
        lines = script_content.split("\n")
        for i, line in enumerate(lines):
            if "\"Approved\"" in line or "'Approved'" in line:
                print(f"  Line {i+1}: {line.strip()}")
