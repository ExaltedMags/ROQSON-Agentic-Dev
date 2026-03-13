import roqson

print_format_html = """
<style>
    .billing-statement {
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.4;
        color: #000;
        page-break-after: always;
    }
    .billing-statement:last-child {
        page-break-after: auto;
    }
    .billing-table th, .billing-table td {
        border: 1px solid #000;
        padding: 6px;
    }
    .billing-table th {
        text-align: center;
        font-weight: bold;
    }
    .text-center { text-align: center; }
    .text-right { text-align: right; }
    .header-row { margin-bottom: 20px; }
    .signature-box { border-bottom: 1px solid #000; height: 30px; margin-bottom: 5px; }
</style>

{% set sales_docs = [] %}
{% for row in doc.table_cpme %}
    {% set s = frappe.get_doc("Sales", row.sales_no) %}
    {% if s not in sales_docs %}
        {% set _ = sales_docs.append(s) %}
    {% endif %}
{% endfor %}

{# Group sales by customer #}
{% set customers = [] %}
{% for s in sales_docs %}
    {% set cust_key = s.customer_name ~ "||" ~ (s.address or "") %}
    {% if cust_key not in customers %}
        {% set _ = customers.append(cust_key) %}
    {% endif %}
{% endfor %}

{% for cust_key in customers %}
    {% set cust_name = cust_key.split("||")[0] %}
    {% set cust_addr = cust_key.split("||")[1] %}
    
    {# Get all sales for this customer in this trip #}
    {% set cust_sales = [] %}
    {% for s in sales_docs %}
        {% set s_key = s.customer_name ~ "||" ~ (s.address or "") %}
        {% if s_key == cust_key %}
            {% set _ = cust_sales.append(s) %}
        {% endif %}
    {% endfor %}

    <div class="billing-statement">
        <h3 class="text-center" style="margin-bottom: 20px; text-transform: uppercase;">Billing Statement</h3>
        
        <table style="width: 100%; margin-bottom: 20px; border-collapse: collapse;">
            <tr>
                <td style="width: 60%; vertical-align: top; padding-right: 15px;">
                    <div style="margin-bottom: 10px;">
                        <strong>Customer:</strong> {{ cust_name }}<br>
                        <strong>Address:</strong> {{ cust_addr }}
                    </div>
                </td>
                <td style="width: 40%; vertical-align: top;">
                    <strong>Date:</strong> {{ frappe.utils.formatdate(doc.date) }}<br>
                    <strong>S.O. No.:</strong> 
                    {% set so_nos = [] %}
                    {% for s in cust_sales %}
                        {% set _ = so_nos.append(s.name) %}
                    {% endfor %}
                    {{ so_nos | join(', ') }}<br>
                    
                    <strong>Ref. No.:</strong> 
                    {% set ref_nos = [] %}
                    {% for s in cust_sales %}
                        {% if s.order_ref and s.order_ref not in ref_nos %}
                            {% set _ = ref_nos.append(s.order_ref) %}
                        {% endif %}
                    {% endfor %}
                    {{ ref_nos | join(', ') }}<br>
                    
                    <strong>Terms:</strong>
                    {% set terms = [] %}
                    {% for s in cust_sales %}
                        {% if s.terms and s.terms not in terms %}
                            {% set _ = terms.append(s.terms) %}
                        {% endif %}
                    {% endfor %}
                    {{ terms | join(', ') }}<br>

                    <strong>Salesman:</strong>
                    {% set salesmen = [] %}
                    {% for s in cust_sales %}
                        {% set so_doc = frappe.get_doc("Order Form", s.order_ref) if s.order_ref else None %}
                        {% set s_man = frappe.db.get_value("User", so_doc.owner, "full_name") if so_doc else frappe.db.get_value("User", s.owner, "full_name") %}
                        {% set s_man = s_man or so_doc.owner if so_doc else s_man or s.owner %}
                        {% if s_man and s_man not in salesmen %}
                            {% set _ = salesmen.append(s_man) %}
                        {% endif %}
                    {% endfor %}
                    {{ salesmen | join(', ') }}
                </td>
            </tr>
        </table>

        <table class="billing-table" style="width: 100%; border-collapse: collapse; margin-bottom: 20px;">
            <thead>
                <tr>
                    <th style="width: 15%;">QTY</th>
                    <th style="width: 15%;">U/M</th>
                    <th style="width: 55%;">Item Description</th>
                    <th style="width: 15%;">WH</th>
                </tr>
            </thead>
            <tbody>
                {% set total_qty = 0 %}
                {% for s in cust_sales %}
                    {% for item in s.items %}
                        {% set total_qty = total_qty + item.qty %}
                        <tr>
                            <td class="text-center">{{ item.qty }}</td>
                            <td class="text-center">{{ item.unit }}</td>
                            <td>{{ item.item }}</td>
                            <td class="text-center">{{ item.warehouse or '' }}</td>
                        </tr>
                    {% endfor %}
                {% endfor %}
            </tbody>
        </table>

        <div style="margin-bottom: 40px;">
            <strong>Total Qty.:</strong> {{ total_qty }}
        </div>

        <table style="width: 100%; text-align: center; border-collapse: collapse; table-layout: fixed;">
            <tr>
                <td style="padding: 0 10px;">
                    <div class="signature-box"></div>
                    <div>Prepared by</div>
                </td>
                <td style="padding: 0 10px;">
                    <div class="signature-box"></div>
                    <div>Checked by</div>
                </td>
                <td style="padding: 0 10px;">
                    <div class="signature-box"></div>
                    <div>Approved by</div>
                </td>
                <td style="padding: 0 10px;">
                    <div class="signature-box">
                        {% if doc.assigned_drivers_display %}
                            {{ doc.assigned_drivers_display }}
                        {% endif %}
                    </div>
                    <div>Delivered by</div>
                </td>
            </tr>
        </table>
    </div>
{% endfor %}
"""

format_doc = {
    "doctype": "Print Format",
    "name": "Billing Statement",
    "standard": "No",
    "custom_format": 1,
    "print_format_builder": 0,
    "doc_type": "Trip Ticket",
    "module": "Core",
    "html": print_format_html,
    "print_format_type": "Jinja"
}

try:
    existing = roqson.get_doc("Print Format", "Billing Statement")
    print("Found existing Print Format, updating...")
    roqson.update_doc("Print Format", "Billing Statement", {"html": print_format_html})
    print("Updated Print Format: Billing Statement")
except Exception as e:
    print("Creating new Print Format...")
    res = roqson.call_method("frappe.client.insert", doc=format_doc)
    print("Created Print Format: Billing Statement", res.get("message", {}).get("name"))

