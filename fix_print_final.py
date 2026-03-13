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
    .error-msg { color: red; padding: 20px; border: 1px solid red; font-weight: bold; }
</style>

{% set table_rows = doc.get("table_cpme") or [] %}

{% if not table_rows %}
    <div class="error-msg">
        <h4>No Sales Records Linked</h4>
        <p>Please add sales records to this Trip Ticket before printing.</p>
    </div>
{% else %}
    {# 1. Collect all valid Sales documents linked in this trip #}
    {% set sales_docs = [] %}
    {% for row in table_rows %}
        {% if row.sales_no %}
            {% set s_doc = frappe.get_doc("Sales", row.sales_no) %}
            {% if s_doc %}
                {% set _ = sales_docs.append(s_doc) %}
            {% endif %}
        {% endif %}
    {% endfor %}

    {% if not sales_docs %}
        <div class="error-msg">
            <h4>Billing Data Not Found</h4>
            <p>Could not load the linked Sales records. Verify the Sales numbers are correct.</p>
        </div>
    {% else %}
        {# 2. Group these Sales docs by Customer (Name + Address) #}
        {% set customer_keys = [] %}
        {% set customer_data = {} %}

        {% for s in sales_docs %}
            {% set c_name = s.customer_name or "Unknown Customer" %}
            {% set c_addr = s.address or "No Address Provided" %}
            {% set key = c_name ~ "||" ~ c_addr %}
            
            {% if key not in customer_keys %}
                {% set _ = customer_keys.append(key) %}
                {% set _ = customer_data.update({key: []}) %}
            {% endif %}
            {% set _ = customer_data[key].append(s) %}
        {% endfor %}

        {# 3. Render one Billing Statement per Customer #}
        {% for key in customer_keys %}
            {% set parts = key.split("||") %}
            {% set cust_name = parts[0] %}
            {% set cust_addr = parts[1] %}
            {% set current_sales_list = customer_data[key] %}

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
                        <td style="width: 40%; vertical-align: top; border-left: 1px solid #eee; padding-left: 15px;">
                            <strong>Date:</strong> {{ frappe.utils.formatdate(doc.date) if doc.date else '' }}<br>
                            
                            <strong>S.O. No.:</strong> 
                            {% set so_nos = [] %}
                            {% for s in current_sales_list %}
                                {% set _ = so_nos.append(s.name) %}
                            {% endfor %}
                            {{ so_nos | join(', ') }}<br>
                            
                            <strong>Ref. No.:</strong> 
                            {% set ref_nos = [] %}
                            {% for s in current_sales_list %}
                                {% if s.order_ref and s.order_ref not in ref_nos %}
                                    {% set _ = ref_nos.append(s.order_ref) %}
                                {% endif %}
                            {% endfor %}
                            {{ ref_nos | join(', ') }}<br>
                            
                            <strong>Terms:</strong>
                            {% set terms_list = [] %}
                            {% for s in current_sales_list %}
                                {% if s.terms and s.terms not in terms_list %}
                                    {% set _ = terms_list.append(s.terms) %}
                                {% endif %}
                            {% endfor %}
                            {{ terms_list | join(', ') }}<br>

                            <strong>Salesman:</strong>
                            {% set salesmen = [] %}
                            {% for s in current_sales_list %}
                                {% set s_man_id = frappe.db.get_value("Order Form", s.order_ref, "owner") if s.order_ref else s.owner %}
                                {% if s_man_id %}
                                    {% set s_name = frappe.db.get_value("User", s_man_id, "full_name") or s_man_id %}
                                    {% if s_name not in salesmen %}
                                        {% set _ = salesmen.append(s_name) %}
                                    {% endif %}
                                {% endif %}
                            {% endfor %}
                            {{ salesmen | join(', ') }}
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
                        {% set total_qty_obj = {"val": 0} %}
                        {% for s in current_sales_list %}
                            {% for item in (s.items or []) %}
                                {% set _ = total_qty_obj.update({"val": total_qty_obj.val + (item.qty | float)}) %}
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

                <div style="margin-bottom: 40px;">
                    <strong>Total Qty.:</strong> {{ total_qty_obj.val }}
                </div>

                <table style="width: 100%; text-align: center; border-collapse: collapse; table-layout: fixed;">
                    <tr>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px;">Prepared by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px;">Checked by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box"></div>
                            <div style="font-size: 10px;">Approved by</div>
                        </td>
                        <td style="padding: 0 10px;">
                            <div class="signature-box" style="display: flex; align-items: flex-end; justify-content: center; padding-bottom: 2px;">
                                {{ doc.assigned_drivers_display or '' }}
                            </div>
                            <div style="font-size: 10px;">Delivered by</div>
                        </td>
                    </tr>
                </table>
            </div>
        {% endfor %}
    {% endif %}
{% endif %}
"""

try:
    print("Updating Print Format with full styled template...")
    roqson.update_doc("Print Format", "Billing Statement", {"html": print_format_html})
    print("Update successful!")
except Exception as e:
    print(f"Update failed: {e}")
