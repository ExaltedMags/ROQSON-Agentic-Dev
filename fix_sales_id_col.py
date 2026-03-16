import roqson
import json

with open("sales_list_script.js", "r", encoding="utf-8") as f:
    content = f.read()

# Update widths
content = content.replace('var SL_ROW_MIN = "1470px";', 'var SL_ROW_MIN = "1630px";')
content = content.replace('min-width:1470px !important;', 'min-width:1630px !important;')

old_css = """#page-List\\\\/Sales\\\\/List .list-subject {\\
    flex:0 0 40px !important; min-width:40px !important; max-width:40px !important;\\
    overflow:hidden !important;\\
}\\
#page-List\\\\/Sales\\\\/List .list-subject .level-item.bold,\\
#page-List\\\\/Sales\\\\/List .list-subject .level-item.ellipsis,\\
#page-List\\\\/Sales\\\\/List .list-subject .bold,\\
#page-List\\\\/Sales\\\\/List .list-subject a.ellipsis,\\
#page-List\\\\/Sales\\\\/List .list-header-subject .list-subject-title,\\
#page-List\\\\/Sales\\\\/List .list-header-subject .list-header-meta { display:none !important; }\\"""

new_css = """#page-List\\\\/Sales\\\\/List .list-subject {\\
    flex:0 0 200px !important; min-width:200px !important; max-width:200px !important;\\
    overflow:hidden !important; display: flex !important; align-items: center !important;\\
}\\
#page-List\\\\/Sales\\\\/List .list-header-subject .list-header-meta { display:none !important; }\\"""

if old_css in content:
    content = content.replace(old_css, new_css)
    print("Applying fix via roqson.safe_update_script...")
    roqson.safe_update_script("Client Script", "Sales List Script", content)
else:
    print("Could not find the exact CSS block to replace.")
