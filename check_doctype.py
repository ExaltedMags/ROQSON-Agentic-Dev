import roqson
import json

doc = roqson.get_doc("DocType", "Order Form")
fields = doc.get("fields", [])

child_tables = []
for f in fields:
    if f.get("fieldtype") == "Table":
        child_tables.append((f.get("fieldname"), f.get("options")))

print(f"Child tables: {child_tables}")

# Check the fields of the main child table (assuming it's the first one or table_mkaq)
for fieldname, options in child_tables:
    if fieldname == "table_mkaq":
        child_doc = roqson.get_doc("DocType", options)
        child_fields = child_doc.get("fields", [])
        field_names = [cf.get("fieldname") for cf in child_fields]
        print(f"\nFields in {options} (table_mkaq):")
        print(field_names)
