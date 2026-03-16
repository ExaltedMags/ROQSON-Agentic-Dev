import roqson
scripts = roqson.get_scripts_for_doctype('Trip Ticket')

print("\nClient Scripts for Trip Ticket:")
for s in scripts['client']:
    status = "enabled" if s.get("enabled") else "disabled"
    print(f"  [{status}] {s['name']}")

print("\nServer Scripts for Trip Ticket:")
for s in scripts['server']:
    status = "disabled" if s.get("disabled") else "active"
    print(f"  [{status}] {s['name']} ({s['script_type']})")
