import roqson

print("Fetching all Sales records...")
sales_records = roqson.list_docs('Sales', fields=['name', 'status', 'fulfillment_type'])

count = 0
for s in sales_records:
    if s.get('status') == 'Unpaid':
        print(f"Updating {s['name']} to Pending...")
        data = {"status": "Pending"}
        if not s.get('fulfillment_type'):
            data["fulfillment_type"] = "Delivery"
        
        try:
            roqson.update_doc("Sales", s['name'], data)
            count += 1
        except Exception as e:
            print(f"Error updating {s['name']}: {e}")

print(f"Migration complete. Updated {count} records.")
