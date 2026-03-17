import frappe

# Customer Information DocType Event handlers — populated in Phase 5.7.
# 3 scripts to port (Archive CI goes to permissions.py, not here).


def before_save(doc, method):
    # Merged from Server Scripts: "CI: Unlimited Credit Set" + "Customer Information: Fields Validation"

    # CI: Unlimited Credit Set
    if doc.is_unlimited_credit:
        doc.credit_limit = None

    # Customer Information: Fields Validation
    def validate_email(email, label):
        if not email:
            return
        if "@" not in email or "." not in email.split("@")[-1]:
            frappe.throw(label + " must be a valid email address")

    validate_email(doc.business_email_address, "Business email address")
    validate_email(doc.email_address, "Email address")

    if doc.name_of_business and doc.name_of_business.isdigit():
        frappe.throw("Name of business cannot contain numbers only")

    if doc.owners_full_name and doc.owners_full_name.isdigit():
        frappe.throw("Owner's full name cannot contain numbers only")

    if doc.contact_person and doc.contact_person.isdigit():
        frappe.throw("Contact person cannot contain numbers only")

    if doc.tin_number:
        tin = doc.tin_number.replace("-", "").replace(" ", "")
        if not tin.isdigit():
            frappe.throw("TIN must contain digits only")
        if len(tin) not in (9, 12):
            frappe.throw("TIN must be 9 or 12 digits")
        doc.tin_number = tin

    def validate_mobile(num, label):
        if not num:
            return num
        cleaned = num.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if cleaned.startswith("+63"):
            cleaned = "0" + cleaned[3:]
        elif cleaned.startswith("63"):
            cleaned = "0" + cleaned[2:]
        if not cleaned.isdigit():
            frappe.throw(label + " must contain digits only")
        if len(cleaned) != 11 or not cleaned.startswith("09"):
            frappe.throw(label + " must be a valid Philippine mobile number")
        return cleaned

    doc.business_mobile_address = validate_mobile(doc.business_mobile_address, "Business mobile number")
    doc.phone_number = validate_mobile(doc.phone_number, "Phone number")
    doc.secondary_contact_no = validate_mobile(doc.secondary_contact_no, "Secondary contact number")

    if doc.landline_number:
        landline = doc.landline_number.replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
        if not landline.isdigit():
            frappe.throw("Landline number must contain digits only")
        if not (7 <= len(landline) <= 10):
            frappe.throw("Landline number must be between 7 and 10 digits")
        doc.landline_number = landline

    if doc.year_established:
        current_year = frappe.utils.now_datetime().year
        if not (1900 <= doc.year_established <= current_year):
            frappe.throw("Year established must be between 1900 and the current year")


def on_update_after_submit(doc, method):
    # Ported from Server Script: "CI: Allow Edit After Subm"
    allowed_roles = ["Manager", "President"]
    restricted_fields = ["name_of_business", "owners_full_name"]

    user_roles = frappe.get_all(
        "Has Role",
        filters={"parent": frappe.session.user},
        pluck="role"
    )

    for field in restricted_fields:
        if doc.has_value_changed(field):
            has_permission = any(role in user_roles for role in allowed_roles)
            if not has_permission:
                frappe.throw(
                    "You are not authorized to modify business identity details after submission."
                )
