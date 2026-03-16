import roqson

script_name = "Sales List Script"
doc = roqson.get_doc("Client Script", script_name)
content = doc["script"]

# Add .row-locked CSS
old_css = """#page-List\\\\/Sales\\\\/List .list-row-head .list-row-col.hidden-md {\\
    display:flex !important;\\
}\\
';"""

new_css = """#page-List\\\\/Sales\\\\/List .list-row-head .list-row-col.hidden-md {\\
    display:flex !important;\\
}\\
.row-locked { opacity: 0.5; background-color: #f9f9f9 !important; pointer-events: none; }\\
';"""

content = content.replace(old_css, new_css)

# Add event listener
old_onload_end = """                    listview.filter_area.filter_list.apply();
                }
            });
        }
    },"""

new_onload_end = """                    listview.filter_area.filter_list.apply();
                }
            });
        }
        
        // Bind selection lock to checkbox changes
        listview.$result.on("change", ".list-row-checkbox", () => {
            frappe.listview_settings["Sales"].handle_selection_lock(listview);
        });
    },"""

content = content.replace(old_onload_end, new_onload_end)

print("Applying missing selection lock triggers and styles via roqson.safe_update_script...")
roqson.safe_update_script("Client Script", script_name, content)
