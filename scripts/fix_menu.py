import psycopg2
import json

print("=" * 80)
print("=== REGISTERING HOURLY ACTIVITY LOG VIEW, ACTION & MENU ===")
print("=" * 80)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# 1. Ensure ir_model
cr.execute("SELECT id FROM ir_model WHERE model = 'crm.hourly.activity.log';")
row = cr.fetchone()
if not row:
    cr.execute("""
        INSERT INTO ir_model (model, name, state)
        VALUES ('crm.hourly.activity.log', '{"en_US": "Hourly Activity Log"}'::jsonb, 'base')
        RETURNING id;
    """)
    model_id = cr.fetchone()[0]
    print(f"✓ Created ir_model ID: {model_id}")
else:
    model_id = row[0]
    print(f"✓ Found ir_model ID: {model_id}")

# 2. Ensure ir_model_fields
fields_to_add = [
    ('activity_date', 'Date', 'date', None),
    ('user_id', 'Salesperson', 'many2one', 'res.users'),
    ('h08_09', '8am to 9am', 'integer', None),
    ('h09_10', '9am to 10am', 'integer', None),
    ('h10_11', '10am to 11am', 'integer', None),
    ('h11_12', '11am to 12pm', 'integer', None),
    ('h12_01', '12pm to 1pm', 'integer', None),
    ('h02_03', '2pm to 3pm', 'integer', None),
    ('h03_04', '3pm to 4pm', 'integer', None),
    ('h04_05', '4pm to 5pm', 'integer', None),
    ('total_count', 'Total', 'integer', None),
]

for fname, fstring, ftype, frel in fields_to_add:
    cr.execute("SELECT id FROM ir_model_fields WHERE model = 'crm.hourly.activity.log' AND name = %s;", (fname,))
    if not cr.fetchone():
        cr.execute("""
            INSERT INTO ir_model_fields (model_id, model, name, field_description, ttype, relation, state)
            VALUES (%s, 'crm.hourly.activity.log', %s, %s::jsonb, %s, %s, 'base');
        """, (model_id, fname, json.dumps({'en_US': fstring}), ftype, frel))
        print(f"  + Added field '{fname}' ({ftype})")

# 3. Ensure ir_model_access
cr.execute("SELECT id FROM ir_model_access WHERE model_id = %s;", (model_id,))
if not cr.fetchone():
    cr.execute("SELECT id FROM ir_model_data WHERE module = 'base' AND name = 'group_user';")
    group_user_id = cr.fetchone()[0]
    cr.execute("""
        INSERT INTO ir_model_access (name, model_id, group_id, perm_read, perm_write, perm_create, perm_unlink)
        VALUES ('access_crm_hourly_activity_log', %s, %s, true, false, false, false);
    """, (model_id, group_user_id))
    print("✓ Granted read access to base.group_user")

# 4. Ensure List View
list_arch = """<list string="Hourly Activity Log" default_order="activity_date desc, total_count desc" create="0" delete="0" edit="0">
    <field name="user_id" widget="many2one_avatar_user" string="Salesperson"/>
    <field name="h08_09" string="8am to 9am" sum="Total 8am-9am"/>
    <field name="h09_10" string="9am to 10am" sum="Total 9am-10am"/>
    <field name="h10_11" string="10am to 11am" sum="Total 10am-11am"/>
    <field name="h11_12" string="11am to 12pm" sum="Total 11am-12pm"/>
    <field name="h12_01" string="12pm to 1pm" sum="Total 12pm-1pm"/>
    <field name="h02_03" string="2pm to 3pm" sum="Total 2pm-3pm"/>
    <field name="h03_04" string="3pm to 4pm" sum="Total 3pm-4pm"/>
    <field name="h04_05" string="4pm to 5pm" sum="Total 4pm-5pm"/>
    <field name="total_count" string="Total" sum="Grand Total"/>
</list>"""

cr.execute("SELECT id FROM ir_ui_view WHERE model = 'crm.hourly.activity.log' AND type = 'list';")
row = cr.fetchone()
if row:
    list_view_id = row[0]
    cr.execute("UPDATE ir_ui_view SET arch_db = %s::jsonb, mode = 'primary' WHERE id = %s;", (json.dumps({'en_US': list_arch}), list_view_id))
    print(f"✓ Updated List View ID: {list_view_id}")
else:
    cr.execute("""
        INSERT INTO ir_ui_view (name, model, type, arch_db, priority, mode)
        VALUES ('crm.hourly.activity.log.list', 'crm.hourly.activity.log', 'list', %s::jsonb, 16, 'primary')
        RETURNING id;
    """, (json.dumps({'en_US': list_arch}),))
    list_view_id = cr.fetchone()[0]
    print(f"✓ Created List View ID: {list_view_id}")

# 5. Ensure Search View
search_arch = """<search string="Search Hourly Activity Log">
    <field name="user_id" string="Salesperson"/>
    <field name="activity_date" string="Date"/>
    <separator/>
    <filter string="Today" name="filter_today" domain="[('activity_date', '=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Yesterday" name="filter_yesterday" domain="[('activity_date', '=', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))]"/>
    <filter string="Last 7 Days" name="filter_last_7_days" domain="[('activity_date', '&gt;=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d'))]"/>
    <filter string="Last 2 Weeks" name="filter_last_2_weeks" domain="[('activity_date', '&gt;=', (context_today() - datetime.timedelta(days=14)).strftime('%Y-%m-%d'))]"/>
    <filter string="This Month" name="filter_this_month" domain="[('activity_date', '&gt;=', context_today().strftime('%Y-%m-01'))]"/>
    <separator/>
    <filter string="My Activities" name="my_activities" domain="[('user_id', '=', uid)]"/>
    <separator/>
    <group expand="0" string="Group By">
        <filter string="Date" name="group_by_date" context="{'group_by': 'activity_date'}"/>
        <filter string="Salesperson" name="group_by_user" context="{'group_by': 'user_id'}"/>
    </group>
</search>"""

cr.execute("SELECT id FROM ir_ui_view WHERE model = 'crm.hourly.activity.log' AND type = 'search';")
row = cr.fetchone()
if row:
    search_view_id = row[0]
    cr.execute("UPDATE ir_ui_view SET arch_db = %s::jsonb, mode = 'primary' WHERE id = %s;", (json.dumps({'en_US': search_arch}), search_view_id))
    print(f"✓ Updated Search View ID: {search_view_id}")
else:
    cr.execute("""
        INSERT INTO ir_ui_view (name, model, type, arch_db, priority, mode)
        VALUES ('crm.hourly.activity.log.search', 'crm.hourly.activity.log', 'search', %s::jsonb, 16, 'primary')
        RETURNING id;
    """, (json.dumps({'en_US': search_arch}),))
    search_view_id = cr.fetchone()[0]
    print(f"✓ Created Search View ID: {search_view_id}")

# 6. Ensure Window Action
cr.execute("SELECT id FROM ir_act_window WHERE res_model = 'crm.hourly.activity.log';")
row = cr.fetchone()
if row:
    action_id = row[0]
    cr.execute("""
        UPDATE ir_act_window 
        SET name = '{"en_US": "Hourly Activity Log"}'::jsonb,
            view_id = %s,
            search_view_id = %s,
            context = %s,
            binding_type = 'action',
            binding_view_types = 'list,form',
            target = 'current'
        WHERE id = %s;
    """, (list_view_id, search_view_id, "{'search_default_filter_today': 1}", action_id))
    print(f"✓ Updated Window Action ID: {action_id}")
else:
    cr.execute("""
        INSERT INTO ir_act_window (name, res_model, view_mode, view_id, search_view_id, context, type, binding_type, binding_view_types, target)
        VALUES ('{"en_US": "Hourly Activity Log"}'::jsonb, 'crm.hourly.activity.log', 'list', %s, %s, %s, 'ir.actions.act_window', 'action', 'list,form', 'current')
        RETURNING id;
    """, (list_view_id, search_view_id, "{'search_default_filter_today': 1}"))
    action_id = cr.fetchone()[0]
    print(f"✓ Created Window Action ID: {action_id}")

# 7. Ensure Top Menu Item under CRM (parent_id = 451)
cr.execute("""
    SELECT id FROM ir_ui_menu 
    WHERE parent_id = 451 AND name->>'en_US' = 'Hourly Activity Log';
""")
row = cr.fetchone()
if row:
    menu_id = row[0]
    cr.execute("""
        UPDATE ir_ui_menu 
        SET action = %s, sequence = 5, active = true, parent_path = '451/' || %s || '/'
        WHERE id = %s;
    """, (f"ir.actions.act_window,{action_id}", menu_id, menu_id))
    print(f"✓ Updated Menu ID: {menu_id}")
else:
    cr.execute("""
        INSERT INTO ir_ui_menu (name, parent_id, action, sequence, active, create_uid, write_uid, create_date, write_date)
        VALUES ('{"en_US": "Hourly Activity Log"}'::jsonb, 451, %s, 5, true, 1, 1, NOW(), NOW())
        RETURNING id;
    """, (f"ir.actions.act_window,{action_id}",))
    menu_id = cr.fetchone()[0]
    cr.execute("UPDATE ir_ui_menu SET parent_path = %s WHERE id = %s;", (f"451/{menu_id}/", menu_id))
    print(f"✓ Created Menu ID: {menu_id}")

# Add ir_model_data references for action, views, and menu
data_entries = [
    ('crm_import', 'crm_hourly_activity_log_view_tree', 'ir.ui.view', list_view_id),
    ('crm_import', 'crm_hourly_activity_log_view_search', 'ir.ui.view', search_view_id),
    ('crm_import', 'action_crm_hourly_activity_log', 'ir.actions.act_window', action_id),
    ('crm_import', 'crm_menu_hourly_activity_log', 'ir.ui.menu', menu_id),
]

for mod, xml_name, model_type, res_id in data_entries:
    cr.execute("SELECT id FROM ir_model_data WHERE module = %s AND name = %s;", (mod, xml_name))
    if not cr.fetchone():
        cr.execute("""
            INSERT INTO ir_model_data (module, name, model, res_id)
            VALUES (%s, %s, %s, %s);
        """, (mod, xml_name, model_type, res_id))
        print(f"  + Added ir.model.data {mod}.{xml_name}")

conn.commit()
conn.close()
print("\n🎉 HOURLY ACTIVITY LOG FULLY REGISTERED!")
