import roqson
import json

test_jinja = """
{% set customers = [] %}
{% set sales_docs = [] %}
{% for row in doc.table_cpme %}
    {% set s = frappe.get_doc("Sales", row.sales_no) %}
    {% set _ = sales_docs.append(s) %}
    {% set cust_key = s.customer_name ~ "||" ~ (s.address or "") %}
    {% if cust_key not in customers %}
        {% set customers = customers + [cust_key] %}
    {% endif %}
{% endfor %}

Found customers: {{ customers | length }}
{% for c in customers %}
Customer: {{ c.split("||")[0] }}
{% endfor %}
"""

res = roqson.call_method("frappe.client.get", doctype="Trip Ticket", name="TRIP-00082")
# print(res)

print("Jinja test needs to be executed inside Frappe, wait, I can use frappe.render_template via a server script or just rely on standard ERPNext jinja behavior.")
