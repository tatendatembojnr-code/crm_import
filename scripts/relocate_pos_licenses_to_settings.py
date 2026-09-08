import odoo
from odoo import tools, api, sql_db
import os

print("=== RELOCATING POS LICENSES & HIDING DASHBOARD ===", flush=True)

tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm'])
db_name = 'showline_s2_havano_pro_xcynznxmwcotukbxkm'
cr = sql_db.db_connect(db_name).cursor()
env = api.Environment(cr, 2, {})

# Find Settings root menu (base.menu_administration)
settings_menu = env.ref('base.menu_administration', raise_if_not_found=False)
settings_menu_id = settings_menu.id if settings_menu else False
if not settings_menu_id:
    cr.execute("SELECT res_id FROM ir_model_data WHERE module = 'base' AND name = 'menu_administration' LIMIT 1;")
    row = cr.fetchone()
    if row:
        settings_menu_id = row[0]

print(f"Settings root menu ID: {settings_menu_id}", flush=True)

# Find physical path of pos_license_management
try:
    import importlib.util
    mod_spec = importlib.util.find_spec('odoo.addons.pos_license_management')
    if mod_spec:
        print(f"Physical module path: {mod_spec.origin or mod_spec.submodule_search_locations}", flush=True)
except Exception as e:
    print(f"Path search notice: {e}", flush=True)

# Find all POS License menus
cr.execute("""
    SELECT m.id, m.name, m.parent_id, d.module, d.name AS xml_id, m.active
    FROM ir_ui_menu m
    LEFT JOIN ir_model_data d ON d.model = 'ir.ui.menu' AND d.res_id = m.id
    WHERE m.name->>'en_US' ILIKE '%POS License%' 
       OR m.name::text ILIKE '%POS License%'
       OR (d.name IS NOT NULL AND d.name ILIKE '%pos%license%')
       OR (d.module IS NOT NULL AND d.module ILIKE '%pos%license%');
""")
menus = cr.fetchall()
print(f"Found {len(menus)} matching POS license menus:", flush=True)
for r in menus:
    print(f"  ID: {r[0]} | Name: {r[1]} | Parent: {r[2]} | Module: {r[3]} | XML ID: {r[4]} | Active: {r[5]}", flush=True)

# 1. Move root menu (ID 486) under Settings (base.menu_administration)
if settings_menu_id:
    for r in menus:
        menu_id = r[0]
        parent_id = r[2]
        xml_id = r[4]
        
        # If it's the dashboard menu, disable/hide it as requested
        if xml_id and 'dashboard' in xml_id.lower():
            print(f"Hiding Dashboard menu ID {menu_id} ('{xml_id}')...", flush=True)
            cr.execute("UPDATE ir_ui_menu SET active = FALSE WHERE id = %s;", (menu_id,))
        elif not parent_id or parent_id == 1:
            print(f"Ensuring Menu ID {menu_id} is under Settings without web_icon...", flush=True)
            cr.execute("UPDATE ir_ui_menu SET parent_id = %s, web_icon = NULL, active = TRUE WHERE id = %s;", (settings_menu_id, menu_id))
        else:
            # Ensure submenus are active
            cr.execute("UPDATE ir_ui_menu SET active = TRUE WHERE id = %s;", (menu_id,))

    cr.commit()
    print("Database updated: Root POS Licenses moved under Settings and Dashboard hidden.", flush=True)

cr.close()
print("=== POS LICENSE RELOCATION COMPLETE ===", flush=True)
