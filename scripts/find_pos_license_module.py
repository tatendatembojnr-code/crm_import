import odoo
from odoo import tools, api, sql_db

tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm'])
db_name = 'showline_s2_havano_pro_xcynznxmwcotukbxkm'
cr = sql_db.db_connect(db_name).cursor()
env = api.Environment(cr, 2, {})

print("=== ALL INSTALLED MODULES MATCHING LICENSE OR POS ===", flush=True)
cr.execute("""
    SELECT name, state, summary, author
    FROM ir_module_module
    WHERE state = 'installed' AND (name ILIKE '%licen%' OR name ILIKE '%pos%' OR summary ILIKE '%licen%');
""")
for r in cr.fetchall():
    print(f"Module: {r[0]} | Summary: {r[2]} | Author: {r[3]}", flush=True)

print("\n=== MENUS LINKED TO POS LICENSES ===", flush=True)
cr.execute("""
    SELECT m.id, m.name, d.module, d.name AS xml_id, m.parent_id, m.action
    FROM ir_ui_menu m
    LEFT JOIN ir_model_data d ON d.model = 'ir.ui.menu' AND d.res_id = m.id
    WHERE m.name->>'en_US' ILIKE '%License%' OR m.name::text ILIKE '%License%' OR d.name ILIKE '%license%' OR d.module ILIKE '%license%';
""")
for r in cr.fetchall():
    print(f"Menu ID: {r[0]} | Name: {r[1]} | Module: {r[2]} | XML_ID: {r[3]} | Parent: {r[4]} | Action: {r[5]}", flush=True)

cr.close()
