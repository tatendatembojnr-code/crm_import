import subprocess
import json
import xmlrpc.client

print("1. Updating SQL View crm_hourly_activity_log in PostgreSQL...")
sql_script = """
DROP VIEW IF EXISTS crm_hourly_activity_log;

CREATE OR REPLACE VIEW crm_hourly_activity_log AS (
    WITH raw_events AS (
        -- Leads created
        SELECT 
            COALESCE(create_uid, user_id) AS user_id,
            create_date AS event_time
        FROM crm_lead
        WHERE COALESCE(create_uid, user_id) IS NOT NULL AND create_date IS NOT NULL
        
        UNION ALL
        
        -- Leads updated
        SELECT 
            write_uid AS user_id,
            write_date AS event_time
        FROM crm_lead
        WHERE write_uid IS NOT NULL AND write_date IS NOT NULL AND write_date != create_date
        
        UNION ALL
        
        -- Mail activities on CRM leads
        SELECT 
            COALESCE(user_id, create_uid) AS user_id,
            create_date AS event_time
        FROM mail_activity
        WHERE res_model = 'crm.lead' AND create_date IS NOT NULL
        
        UNION ALL
        
        -- Chatter messages / calls / notes logged on CRM leads
        SELECT 
            (SELECT ru.id FROM res_users ru WHERE ru.partner_id = m.author_id LIMIT 1) AS user_id,
            m.create_date AS event_time
        FROM mail_message m
        WHERE m.model = 'crm.lead' AND m.create_date IS NOT NULL AND m.author_id IS NOT NULL
        
        UNION ALL
        
        -- To-Dos created / assigned
        SELECT 
            create_uid AS user_id,
            create_date AS event_time
        FROM todo_task
        WHERE create_date IS NOT NULL AND create_uid IS NOT NULL
    ),
    events_with_hour AS (
        SELECT 
            e.user_id,
            (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
            EXTRACT(HOUR FROM (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg'))::int AS hour_val
        FROM raw_events e
        WHERE e.user_id IS NOT NULL
    )
    SELECT 
        ROW_NUMBER() OVER (ORDER BY eh.activity_date DESC, (
            COUNT(CASE WHEN eh.hour_val = 8 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 9 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 10 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 11 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 12 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 14 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 15 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 16 THEN 1 END)
        ) DESC, eh.user_id ASC) AS id,
        eh.user_id AS user_id,
        eh.activity_date AS activity_date,
        COUNT(CASE WHEN eh.hour_val = 8 THEN 1 END) AS h08_09,
        COUNT(CASE WHEN eh.hour_val = 9 THEN 1 END) AS h09_10,
        COUNT(CASE WHEN eh.hour_val = 10 THEN 1 END) AS h10_11,
        COUNT(CASE WHEN eh.hour_val = 11 THEN 1 END) AS h11_12,
        COUNT(CASE WHEN eh.hour_val = 12 THEN 1 END) AS h12_01,
        COUNT(CASE WHEN eh.hour_val = 14 THEN 1 END) AS h02_03,
        COUNT(CASE WHEN eh.hour_val = 15 THEN 1 END) AS h03_04,
        COUNT(CASE WHEN eh.hour_val = 16 THEN 1 END) AS h04_05,
        (
            COUNT(CASE WHEN eh.hour_val = 8 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 9 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 10 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 11 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 12 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 14 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 15 THEN 1 END) +
            COUNT(CASE WHEN eh.hour_val = 16 THEN 1 END)
        ) AS total_count
    FROM events_with_hour eh
    JOIN res_users u ON u.id = eh.user_id
    WHERE u.active IS TRUE
    GROUP BY eh.user_id, eh.activity_date
    HAVING (
        COUNT(CASE WHEN eh.hour_val = 8 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 9 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 10 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 11 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 12 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 14 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 15 THEN 1 END) +
        COUNT(CASE WHEN eh.hour_val = 16 THEN 1 END)
    ) > 0
);
"""

cmd_psql = [
    "sshpass", "-p", "Farai@#$1234", "ssh",
    "-o", "StrictHostKeyChecking=no",
    "-o", "UserKnownHostsFile=/dev/null",
    "root@127.0.0.1",
    f"docker exec -i psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm"
]
subprocess.run(cmd_psql, input=sql_script, text=True, capture_output=True, check=True)
print("✓ SQL View updated in Postgres with accurate total_count formula and filtering!")

print("\n2. Updating ir_ui_view list and search views in database...")
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

search_arch = """<search string="Search Hourly Activity Log">
    <field name="user_id" string="Salesperson"/>
    <separator/>
    <filter string="Today" name="today" domain="[('activity_date', '=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Yesterday" name="yesterday" domain="[('activity_date', '=', (context_today() - datetime.timedelta(days=1)).strftime('%Y-%m-%d'))]"/>
    <filter string="Last 7 Days" name="last_7_days" domain="[('activity_date', '&gt;=', (context_today() - datetime.timedelta(days=7)).strftime('%Y-%m-%d')), ('activity_date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="Last 2 Weeks" name="last_2_weeks" domain="[('activity_date', '&gt;=', (context_today() - datetime.timedelta(days=14)).strftime('%Y-%m-%d')), ('activity_date', '&lt;=', context_today().strftime('%Y-%m-%d'))]"/>
    <filter string="This Month" name="this_month" domain="[('activity_date', '&gt;=', context_today().strftime('%Y-%m-01'))]"/>
    <separator/>
    <filter string="My Activities" name="my_activities" domain="[('user_id', '=', uid)]"/>
    <separator/>
    <group expand="0" string="Group By">
        <filter string="Date" name="group_by_date" context="{'group_by': 'activity_date'}"/>
        <filter string="Salesperson" name="group_by_user" context="{'group_by': 'user_id'}"/>
    </group>
</search>"""

sql_views_update = f"""
UPDATE ir_ui_view 
SET arch_db = '{json.dumps({"en_US": list_arch})}'::jsonb 
WHERE model = 'crm.hourly.activity.log' AND type = 'list';

UPDATE ir_ui_view 
SET arch_db = '{json.dumps({"en_US": search_arch})}'::jsonb 
WHERE model = 'crm.hourly.activity.log' AND type = 'search';

UPDATE ir_act_window
SET context = '{{"search_default_today": 1}}'
WHERE res_model = 'crm.hourly.activity.log';
"""
subprocess.run(cmd_psql, input=sql_views_update, text=True, capture_output=True, check=True)
print("✓ ir_ui_view list, search, and action default context updated!")

print("\n3. Verifying updated data via XML-RPC...")
url = 'http://localhost:9060'
db = 'showline_s2_havano_pro_xcynznxmwcotukbxkm'
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, 'admin', 'Admin@Odoo1234!', {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

records = models.execute_kw(db, uid, 'Admin@Odoo1234!', 'crm.hourly.activity.log', 'search_read', [[('activity_date', '=', '2026-09-14')]], {'fields': ['user_id', 'h08_09', 'h09_10', 'h10_11', 'h11_12', 'h12_01', 'h02_03', 'h03_04', 'h04_05', 'total_count'], 'order': 'total_count desc'})

print(f"{'Salesperson':<25} | 8-9 | 9-10 | 10-11 | 11-12 | 12-1 | 2-3 | 3-4 | 4-5 | Total | Match?")
print('-' * 95)
for r in records:
    name = r['user_id'][1] if r['user_id'] else 'Unknown'
    sum_hours = r['h08_09'] + r['h09_10'] + r['h10_11'] + r['h11_12'] + r['h12_01'] + r['h02_03'] + r['h03_04'] + r['h04_05']
    match = '✓ YES' if sum_hours == r['total_count'] else '❌ NO'
    print(f"{name:<25} | {r['h08_09']:>3} | {r['h09_10']:>4} | {r['h10_11']:>5} | {r['h11_12']:>5} | {r['h12_01']:>4} | {r['h02_03']:>3} | {r['h03_04']:>3} | {r['h04_05']:>3} | {r['total_count']:>5} | {match}")
