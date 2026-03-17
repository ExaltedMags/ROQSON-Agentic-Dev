app_name = "roqson_core"
app_title = "Roqson Core"
app_publisher = "ROQSON"
app_description = "ROQSON Industrial Sales core customizations"
app_version = "0.0.1"
app_license = "MIT"

# Fixtures — populated in Phase 4 (Custom Fields + Print Formats)
#            Phase 8 (DocType JSON)
#            Phase 9 (Workflow JSON)
fixtures = []

# DocType event hooks — populated in Phase 5
# Target state (from ARCHITECTURE.md):
#
# doc_events = {
#     "Order Form": {
#         "before_delete":           "roqson_core.order_form.before_delete",
#         "before_save":             "roqson_core.order_form.before_save",
#         "before_submit":           "roqson_core.order_form.before_submit",
#         "after_save":              "roqson_core.order_form.after_save",
#         "on_update_after_submit":  "roqson_core.order_form.on_update_after_submit",
#         "on_submit":               "roqson_core.order_form.on_submit",
#         "on_cancel":               "roqson_core.order_form.on_cancel",
#     },
#     "Trips": {
#         "before_insert":           "roqson_core.trips.before_insert",
#         "before_validate":         "roqson_core.trips.before_validate",
#         "before_save":             "roqson_core.trips.before_save",
#         "after_insert":            "roqson_core.trips.after_insert",
#         "after_save":              "roqson_core.trips.after_save",
#     },
#     "Credit Application": {
#         "before_save":             "roqson_core.credit_application.before_save",
#         "before_submit":           "roqson_core.credit_application.before_submit",
#         "after_save":              "roqson_core.credit_application.after_save",
#         "on_update_after_submit":  "roqson_core.credit_application.on_update_after_submit",
#     },
#     "Customer Information": {
#         "before_save":             "roqson_core.customer_information.before_save",
#         "on_update_after_submit":  "roqson_core.customer_information.on_update_after_submit",
#     },
#     "Sales": {
#         "before_save":             "roqson_core.sales.before_save",
#         "after_save":              "roqson_core.sales.after_save",
#     },
#     "Receipt": {
#         "before_cancel":           "roqson_core.receipt.before_cancel",
#         "on_submit":               "roqson_core.receipt.on_submit",
#     },
#     "Price Change Request": {
#         "after_save":              "roqson_core.price_change_request.after_save",
#     },
#     "Cost Tier": {
#         "before_save":             "roqson_core.cost_tier.before_save",
#     },
#     "Inventory Entry": {
#         "after_insert":            "roqson_core.inventory_entry.after_insert",
#     },
#     "Inventory Ledger": {
#         "before_insert":           "roqson_core.inventory_ledger.before_insert",
#         "after_insert":            "roqson_core.inventory_ledger.after_insert",
#         "on_update_after_submit":  "roqson_core.inventory_ledger.on_update_after_submit",
#     },
# }
doc_events = {}

# Permission query conditions — populated in Phase 6
# Target state (from ARCHITECTURE.md):
#
# permission_query_conditions = {
#     "Order Form":           "roqson_core.permissions.get_order_form_conditions",
#     "Trips":                "roqson_core.permissions.get_trips_conditions",
#     "Sales":                "roqson_core.permissions.get_sales_conditions",
#     "Credit Application":   "roqson_core.permissions.get_credit_application_conditions",
#     "Customer Survey Form": "roqson_core.permissions.get_customer_survey_form_conditions",
#     "Customer Information": "roqson_core.permissions.get_customer_information_conditions",
#     "Product":              "roqson_core.permissions.get_product_conditions",
#     "Nature of Business":   "roqson_core.permissions.get_nature_of_business_conditions",
#     "Promos":               "roqson_core.permissions.get_promos_conditions",
#     "Discounts":            "roqson_core.permissions.get_discounts_conditions",
#     "Territories":          "roqson_core.permissions.get_territories_conditions",
#     "Vehicles":             "roqson_core.permissions.get_vehicles_conditions",
#     "Warehouses":           "roqson_core.permissions.get_warehouses_conditions",
#     "Brands":               "roqson_core.permissions.get_brands_conditions",
#     "Sales Personnel":      "roqson_core.permissions.get_sales_personnel_conditions",
# }
permission_query_conditions = {}

# Scheduler tasks — populated in Phase 7
# Target state:
#
# scheduler_events = {
#     "daily":  ["roqson_core.tasks.auto_archive_expired_promos"],
#     "hourly": ["roqson_core.tasks.notify_overheld_reservations"],
# }
scheduler_events = {}
