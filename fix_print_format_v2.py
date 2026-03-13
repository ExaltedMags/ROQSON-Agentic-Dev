import roqson

print_format_html = """
<style>
    .billing-statement {
        font-family: Arial, sans-serif;
        font-size: 12px;
        line-height: 1.4;
        color: #000;
        page-break-after: always;
        padding: 20px;
    }
    .billing-statement:last-child {
        page-break-after: auto;
    }
    .billing-table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
    }
    .billing-table th, .billing-table td {
        border: 1px solid #000;
        padding: 6px;
    }
    .billing-table th {
        text-align: center;
        font-weight: bold;
        background-color: #f2f2f2;
    }
    .text-center { text-align: center; }
    .text-right { text-align: right; }
    .signature-box { border-bottom: 1px solid #000; height: 30px; margin-bottom: 5px; }
    .error-msg { color: red; padding: 20px; border: 1px solid red; }
</style>

{% set sales_docs = [] %}
{% set table_rows = doc.get("table_cpme") or [] %}

{% if not table_rows %}
    <div class="error-msg">
        <h4>No Sales Records Linked</h4>
        <p>This Trip Ticket does not have any sales records in the item table. Please add sales records to generate a billing statement.</p>
    </div>
{% else %}
    {% for row in table_rows %}
        {% if row.sales_no %}
            {% try %}
                {% set s = frappe.get_doc("Sales", row.sales_no) %}
                {% if s not in sales_docs %}
                    {% set _ = sales_docs.append(s) %}
                {% endif %}
            {% except %}
                <!-- Sales document {{ row.sales_no }} not found or inaccessible -->
            {% endtry %}
        {% endif %}
    {% endfor %}

    {% if not sales_docs %}
        <div class="error-msg">
            <h4>Billing Data Not Found</h4>
            <p>Linked Sales records could not be retrieved. Please verify the Sales numbers in the Trip Ticket.</p>
        </div>
    {% else %}
        {# Group sales by customer key (Name + Address) #}
        {% set customers = [] %}
        {% set customer_map = {} %}
        
        {% for s in sales_docs %}
            {% set c_name = s.customer_name or "Unknown Customer" %}
            {% set c_addr = s.address or "No Address Provided" %}
            {% set cust_key = c_name ~ "||" ~ c_addr %}
            
            {% if cust_key not in customers %}
                {% set _ = customers.append(cust_key) %}
                {% set _ = customer_map.update({cust_key: []}) %}
            {% endif %}
            {% set _ = customer_map[cust_key].append(s) %}
        {% endfor %}

        {% for cust_key in customers %}
            {% set parts = cust_key.split("||") %}
            {% set cust_name = parts[0] %}
            {% set cust_addr = parts[1] %}
            {% set cust_sales = customer_map[cust_key] %}

            <div class="billing-statement">
                <h3 class="text-center" style="margin-bottom: 20px; text-transform: uppercase; letter-spacing: 2px;">Billing Statement</h3>
                
                <table style="width: 100%; margin-bottom: 20px; border-collapse: collapse;">
                    <tr>
                        <td style="width: 60%; vertical-align: top; padding-right: 15px;">
                            <div style="margin-bottom: 10px;">
                                <strong>Customer:</strong> {{ cust_name }}<br>
                                <strong>Address:</strong> {{ cust_addr }}
                            </div>
                        </td>
                        <td style="width: 40%; vertical-align: top; border-left: 1px solid #eee; padding-left: 15px;">
                            <strong>Date:</strong> {{ frappe.utils.formatdate(doc.date) if doc.date else frappe.utils.formatdate(frappe.utils.nowdate()) }}<br>
                            
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
                            {{ ref_nos | join(', ') or 'N/A' }}<br>
                            
                            <strong>Terms:</strong>
                            {% set terms_list = [] %}
                            {% for s in cust_sales %}
                                {% if s.terms and s.terms not in terms_list %}
                                    {% set _ = terms_list.append(s.terms) %}
                                {% endif %}
                            {% endfor %}
                            {{ terms_list | join(', ') or 'N/A' }}<br>

                            <strong>Salesman:</strong>
                            {% set salesmen = [] %}
                            {% for s in cust_sales %}
                                {% set s_man = None %}
                                {% if s.order_ref %}
                                    {% set s_man = frappe.db.get_value("Order Form", s.order_ref, "owner") %}
                                {% endif %}
                                {% if not s_man %}
                                    {% set s_man = s.owner %}
                                {% endif %}
                                
                                {% if s_man %}
                                    {% set full_name = frappe.db.get_value("User", s_man, "full_name") or s_man %}
                                    {% if full_name not in salesmen %}
                                        {% set _ = salesmen.append(full_name) %}
                                    {% endif %}
                                {% endif %}
                            {% endfor %}
                            {{ salesmen | join(', ') or 'N/A' }}
                        </td>
                    </tr>
                </table>

                <table class="billing-table">
                    <thead>
                        <tr>
                            <th style="width: 15%;">QTY</th>
                            <th style="width: 15%;">U/M</th>
                            <th style="width: 55%;">Item Description</th>
                            <th style="width: 15%;">WH</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% set total_qty = [0] %}
                        {% for s in cust_sales %}
                            {% for item in (s.items or []) %}
                                {% set _ = total_qty.append(total_qty.pop() + (item.qty | float)) %}
                                <tr>
                                    <td class="text-center">{{ item.qty }}</td>
                                    <td class="text-center">{{ item.unit or 'PCS' }}</td>
                                    <td>{{ item.item }}</td>
                                    <td class="text-center">{{ item.warehouse or '' }}</td>
                                </tr>
                            {% endfor %}
                        {% endfor %}
                    </tbody>
                </table>

                <div style="margin-bottom: 40px; font-size: 14px;">
                    <strong>Total Qty.:</strong> {{ total_qty[0] }}
                </div>

                <table style="width: 100%; text-align: center; border-collapse: collapse; table-layout: fixed;">
                    <tr>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px; text-transform: uppercase;">Prepared by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px; text-transform: uppercase;">Checked by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px; text-transform: uppercase;">Approved by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box" style="font-weight: bold; font-size: 11px; display: flex; align-items: flex-end; justify-content: center; padding-bottom: 2px;">
                                {{ doc.assigned_drivers_display or '' }}
                            </div>
                            <div style="font-size: 10px; text-transform: uppercase;">Delivered by</div>
                        </td>
                    </tr>
                </table>
            </div>
        {% endfor %}
    {% endif %}
{% endif %}
"""

format_doc_name = "Billing Statement"

try:
    print(f"Updating Print Format: {format_doc_name}")
    roqson.update_doc("Print Format", format_doc_name, {"html": print_format_html})
    print("Update successful!")
except Exception as e:
    print(f"Error updating Print Format: {e}")
