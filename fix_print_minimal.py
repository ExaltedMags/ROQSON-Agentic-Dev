import roqson

# Minimal Jinja that should definitely not crash
# We use .get() and check for existence to be safe
print_format_html = """
<div style="padding: 20px; font-family: sans-serif;">
    <h2 style="text-align: center;">BILLING STATEMENT</h2>
    <hr>
    <p><strong>Trip Ticket:</strong> {{ doc.name }}</p>
    <p><strong>Date:</strong> {{ doc.date or 'N/A' }}</p>
    <p><strong>Driver:</strong> {{ doc.assigned_drivers_display or 'N/A' }}</p>
    
    {% set rows = doc.get("table_cpme") or [] %}
    
    {% if not rows %}
        <div style="color: red; margin: 20px 0;">No Sales records linked to this Trip Ticket.</div>
    {% else %}
        {% for row in rows %}
            <div style="border: 1px solid #ccc; padding: 10px; margin-bottom: 10px;">
                <strong>Sales Order:</strong> {{ row.sales_no }}<br>
                {% if row.sales_no %}
                    {% set s = frappe.get_doc("Sales", row.sales_no) %}
                    <strong>Customer:</strong> {{ s.customer_name or 'Unknown' }}<br>
                    <strong>Address:</strong> {{ s.address or 'N/A' }}<br>
                    
                    <table style="width: 100%; border-collapse: collapse; margin-top: 10px;">
                        <thead>
                            <tr style="background: #eee;">
                                <th style="border: 1px solid #999; padding: 4px;">Qty</th>
                                <th style="border: 1px solid #999; padding: 4px;">Item</th>
                                <th style="border: 1px solid #999; padding: 4px;">WH</th>
                            </tr>
                        </thead>
                        <tbody>
                            {% for item in s.items %}
                            <tr>
                                <td style="border: 1px solid #999; padding: 4px; text-align: center;">{{ item.qty }}</td>
                                <td style="border: 1px solid #999; padding: 4px;">{{ item.item }}</td>
                                <td style="border: 1px solid #999; padding: 4px; text-align: center;">{{ item.warehouse or '' }}</td>
                            </tr>
                            {% endfor %}
                        </tbody>
                    </table>
                {% endif %}
            </div>
        {% endfor %}
    {% endif %}
    
    <div style="margin-top: 30px; display: flex; justify-content: space-between;">
        <div>____________________<br>Prepared by</div>
        <div>____________________<br>Approved by</div>
        <div>____________________<br>Delivered by</div>
    </div>
</div>
"""

try:
    print("Updating Print Format with ultra-safe minimal template...")
    roqson.update_doc("Print Format", "Billing Statement", {"html": print_format_html})
    print("Update successful!")
except Exception as e:
    print(f"Update failed: {e}")
