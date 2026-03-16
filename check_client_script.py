import roqson
import json

doc = roqson.get_doc('Client Script', 'Order Form: Warehouse Assignment')
print(f"Enabled: {doc.get('enabled')}")
print("--- Script ---")
print(doc.get('script'))
