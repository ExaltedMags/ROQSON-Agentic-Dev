import roqson

script_name = "Inventory Stock Out"
old_script = roqson.get_script_body("Server Script", script_name)

# Modify the stock availability check loop
new_script = old_script.replace(
    "            for row in (doc.table_mkaq or []):",
    "            for row in (doc.table_mkaq or []):\n                if row.get('unreserved'):\n                    continue"
)

# Modify the logic where existing ledger is updated
old_update_block = """                for r in ledger.table_jflv:
                    if movement_type == "Reserved":
                        r.qty_reserved = r.qty
                        r.qty_out = 0
                    elif movement_type == "Released":
                        r.qty_reserved = 0
                        r.qty_out = 0
                    elif movement_type == "Out":
                        r.qty_out = r.qty
                        r.qty_reserved = 0
                    elif movement_type == "Return":
                        r.qty_reserved = 0
                        r.qty_out = 0"""

new_update_block = """                for r in ledger.table_jflv:
                    is_unreserved = 0
                    for row in rows:
                        if row.items == r.product:
                            is_unreserved = row.get("unreserved") or 0
                            break

                    if movement_type == "Reserved":
                        r.qty_reserved = 0 if is_unreserved else r.qty
                        r.qty_out = 0
                    elif movement_type == "Released":
                        r.qty_reserved = 0
                        r.qty_out = 0
                    elif movement_type == "Out":
                        r.qty_out = 0 if is_unreserved else r.qty
                        r.qty_reserved = 0
                    elif movement_type == "Return":
                        r.qty_reserved = 0
                        r.qty_out = 0"""

new_script = new_script.replace(old_update_block, new_update_block)

# Modify the logic where new ledger is inserted
old_insert_block = """                for r in rows:
                    ledger.append("table_jflv", {
                        "product": r.items,
                        "unit": r.unit,
                        "qty": r.qty
                    })"""

new_insert_block = """                for r in rows:
                    is_unreserved = r.get("unreserved") or 0
                    ledger.append("table_jflv", {
                        "product": r.items,
                        "unit": r.unit,
                        "qty": r.qty,
                        "qty_reserved": 0 if is_unreserved else (r.qty if movement_type == "Reserved" else 0),
                        "qty_out": 0 if is_unreserved else (r.qty if movement_type == "Out" else 0)
                    })"""

new_script = new_script.replace(old_insert_block, new_insert_block)

roqson.safe_update_script("Server Script", script_name, new_script, auto_confirm=True)
