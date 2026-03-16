import roqson

script_name = "Sales List Script"
doc = roqson.get_doc("Client Script", script_name)
content = doc["script"]

# Add back the banner
old_lock = """    handle_selection_lock: function(listview) {
        setTimeout(function() {
            var selected = listview.get_checked_items();
            listview.$result.find(".list-row-checkbox").prop("disabled", false);
            listview.$result.find(".list-row").removeClass("row-locked");

            if (selected.length > 0) {"""

new_lock = """    handle_selection_lock: function(listview) {
        setTimeout(function() {
            var selected = listview.get_checked_items();
            listview.$result.find(".list-row-checkbox").prop("disabled", false);
            listview.$result.find(".list-row").removeClass("row-locked");
            
            if ($("#selection-hint-msg").length === 0) {
                listview.$result.before('<div id="selection-hint-msg" style="display:none;padding:10px;margin-bottom:10px;background-color:#fcf8e3;border:1px solid #faebcc;color:#8a6d3b;border-radius:4px;font-weight:600;"><i class="fa fa-info-circle"></i> Only Pending Sales records with the same customer and delivery address can be bundled.</div>');
            }

            if (selected.length > 0) {"""
content = content.replace(old_lock, new_lock)

old_lock_slide = """                    }
                });
            } else {
                listview.data.forEach(function(d) {
                    if (d.status !== "Pending" || d.fulfillment_type === "Pick-up") {
                        listview.$result.find('.list-row-checkbox[data-name="' + d.name + '"]').prop("disabled", true);
                    }
                });
            }
        }, 100);
    }"""

new_lock_slide = """                    }
                });
                $("#selection-hint-msg").slideDown(200);
            } else {
                listview.data.forEach(function(d) {
                    if (d.status !== "Pending" || d.fulfillment_type === "Pick-up") {
                        listview.$result.find('.list-row-checkbox[data-name="' + d.name + '"]').prop("disabled", true);
                    }
                });
                $("#selection-hint-msg").slideUp(200);
            }
        }, 100);
    }"""
content = content.replace(old_lock_slide, new_lock_slide)

# Add back the enhanced trip ticket creation
old_btn = """                if (selected.some(function(d) { return d.status !== "Pending"; })) return frappe.msgprint("Only Pending Sales records allowed.");
                if (selected.some(function(d) { return d.fulfillment_type === "Pick-up"; })) return frappe.msgprint("Pick-up orders skip Trip Tickets.");

                frappe.model.with_doctype("Trip Ticket", function() {
                    var tt = frappe.model.get_new_doc("Trip Ticket");
                    tt.outlet   = selected[0].customer_link;
                    tt.address  = selected[0].address;
                    selected.forEach(function(s) {
                        var row = frappe.model.add_child(tt, "table_cpme");
                        row.sales_no = s.name;
                        row.order_no = s.order_ref;
                    });
                    frappe.set_route("Form", "Trip Ticket", tt.name);
                });
            });"""

new_btn = """                if (selected.some(function(d) { return d.status !== "Pending"; })) return frappe.msgprint("Only Pending Sales records allowed.");
                if (selected.some(function(d) { return d.fulfillment_type === "Pick-up"; })) return frappe.msgprint("Pick-up orders skip Trip Tickets.");

                frappe.db.get_doc("Sales", selected[0].name).then(sales_doc => {
                    frappe.model.with_doctype("Trip Ticket", () => {
                        let tt = frappe.model.get_new_doc("Trip Ticket");
                        tt.outlet = sales_doc.customer_link;
                        tt.address = sales_doc.address;
                        tt.contact_number = sales_doc.contact_number;
                        tt.contact_person = sales_doc.contact_person;

                        selected.forEach(s => {
                            let row = frappe.model.add_child(tt, "table_cpme");
                            row.sales_no = s.name;
                            row.order_no = s.order_ref;
                        });
                        frappe.set_route("Form", "Trip Ticket", tt.name);
                    });
                });
            });"""
content = content.replace(old_btn, new_btn)

print("Applying feature restoration via roqson.safe_update_script...")
roqson.safe_update_script("Client Script", script_name, content)
