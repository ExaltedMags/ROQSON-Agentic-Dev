import frappe

# Permission query condition functions — populated in Phase 6.
# 15 functions total: 13 from Permission Query scripts +
#                     2 from misclassified DocType Events (Archive CI, Archive Sales Personnel).
#
# Naming convention: get_<doctype_snake_case>_conditions(user=None) -> str
#
# Functions to implement:
#   get_order_form_conditions, get_trips_conditions, get_sales_conditions,
#   get_credit_application_conditions, get_customer_survey_form_conditions,
#   get_customer_information_conditions, get_product_conditions,
#   get_nature_of_business_conditions, get_promos_conditions,
#   get_discounts_conditions, get_territories_conditions,
#   get_vehicles_conditions, get_warehouses_conditions,
#   get_brands_conditions, get_sales_personnel_conditions
