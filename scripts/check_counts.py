import odoo
from odoo import tools, api, sql_db

tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm'])
db_name = 'showline_s2_havano_pro_xcynznxmwcotukbxkm'
cr = sql_db.db_connect(db_name).cursor()
env = api.Environment(cr, 2, {})

cr.execute("SELECT COUNT(*) FROM crm_lead;")
leads_count = cr.fetchone()[0]

cr.execute("SELECT COUNT(*) FROM mail_activity WHERE res_model = 'crm.lead';")
activities_count = cr.fetchone()[0]

cr.execute("SELECT COUNT(*) FROM mail_message WHERE model = 'crm.lead';")
messages_count = cr.fetchone()[0]

print(f"=== DB CHECK FOR '{db_name}' ===")
print(f"Total CRM Leads: {leads_count}")
print(f"Total Open Activities on Leads: {activities_count}")
print(f"Total Chatter Messages on Leads: {messages_count}")

cr.execute("SELECT id, name, custom_no, create_date FROM crm_lead ORDER BY id DESC LIMIT 5;")
print("Latest 5 Leads in DB:", cr.fetchall())
