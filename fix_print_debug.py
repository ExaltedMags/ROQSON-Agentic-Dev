import roqson

# Absolute minimal template to test if rendering works at all
print_format_html = """
<div style="padding: 50px; text-align: center; border: 5px solid red;">
    <h1>TEST PRINT FORMAT</h1>
    <p>If you see this, the print system is working.</p>
    <p>Ticket Name: {{ doc.name }}</p>
</div>
"""

try:
    print("Updating Print Format with DEBUG template...")
    roqson.update_doc("Print Format", "Billing Statement", {"html": print_format_html})
    print("Update successful!")
except Exception as e:
    print(f"Update failed: {e}")
