import frappe

# API endpoints — populated in Phase 3.
# Each function uses @frappe.whitelist().
# New endpoint path: /api/method/roqson_core.api.<function_name>
#
# 26 functions to port (see ARCHITECTURE.md § api.py):
#   get_product_stock, get_last_outlet_order, get_survey_photos,
#   get_promo_warehouse, get_eligible_orders, stamp,
#   get_active_trip_order_names, get_receipt_history_for_sale,
#   get_receivable_sales_for_customer, get_customer_orders,
#   get_product_inventory,
#   rpm_get_doctype_fields, rpm_get_field_permissions,
#   rpm_get_role_permissions, rpm_get_all_roles, rpm_get_all_doctypes,
#   rpm_update_permission, rpm_update_field_permlevel,
#   rpm_bulk_update_field_permlevels,
#   fix_preferred_datetime_v2, fix_credit_application_table,
#   fix_order_titles_utility, temp_enable_order_form_comments,
#   test_hello, trip_ticket_workflow_updater,
#   trip_ticket_workflow_updater_v2
