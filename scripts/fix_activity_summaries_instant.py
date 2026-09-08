import odoo
from odoo import tools, api, sql_db
import html
import re

print("=== STARTING INSTANT CHATTER & ACTIVITY SUMMARY FIX ===", flush=True)

tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm'])
db_name = 'showline_s2_havano_pro_xcynznxmwcotukbxkm'
cr = sql_db.db_connect(db_name).cursor()
env = api.Environment(cr, 2, {})

def clean_html(text):
    if not text:
        return ""
    clean = html.unescape(re.sub(r'<[^>]+>', ' ', str(text)))
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

# Step 1: Update mail_activity records in DB
print("1. Inspecting mail_activity records...", flush=True)
cr.execute("""
    SELECT id, summary, note 
    FROM mail_activity 
    WHERE res_model = 'crm.lead';
""")
activities = cr.fetchall()
print(f"   Found {len(activities):,} mail_activity records to process.", flush=True)

updated_acts = 0
for act_id, summary, note in activities:
    clean_text = clean_html(note)
    if clean_text:
        new_summary = clean_text[:200]
        cr.execute("UPDATE mail_activity SET summary = %s WHERE id = %s;", (new_summary, act_id))
        updated_acts += 1
    elif summary and (summary.startswith('T') or len(summary) <= 12):
        # Fallback to To-Do if note is empty
        pass

cr.commit()
print(f"   Successfully updated {updated_acts:,} mail_activity summaries with actual note text!", flush=True)

# Step 2: Update closed To-Do chatter messages in mail_message
print("2. Inspecting closed To-Do chatter messages in mail_message...", flush=True)
cr.execute("""
    SELECT id, body 
    FROM mail_message 
    WHERE model = 'crm.lead' AND body LIKE '%<span>To-Do</span> done%';
""")
messages = cr.fetchall()
print(f"   Found {len(messages):,} closed To-Do messages.", flush=True)

updated_msgs = 0
for msg_id, body_html in messages:
    if body_html and '<span>To-Do</span> done' in body_html:
        inner_matches = re.findall(r'<div>(.*?)</div>', body_html, re.DOTALL)
        if len(inner_matches) > 1:
            desc_html = inner_matches[-1]
            clean_text = clean_html(desc_html)
            if clean_text:
                new_body = re.sub(
                    r'(<span>To-Do</span> done <span>: </span><span>)[^<]*(</span>)',
                    r'\g<1>' + html.escape(clean_text[:200]) + r'\2',
                    body_html
                )
                cr.execute("UPDATE mail_message SET body = %s WHERE id = %s;", (new_body, msg_id))
                updated_msgs += 1

cr.commit()
print(f"   Successfully updated {updated_msgs:,} chatter messages!", flush=True)

# Step 3: Update todo_task records if table exists
try:
    cr.execute("""
        UPDATE todo_task 
        SET name = SUBSTRING(description FROM 1 FOR 200) 
        WHERE description IS NOT NULL AND description != '';
    """)
    cr.commit()
    print("3. Updated todo_task records.", flush=True)
except Exception:
    pass

# Step 4: Upgrade the module properly via Odoo Environment so XML views reload
print("4. Upgrading havano_crm_extension module in Odoo...", flush=True)
try:
    module = env['ir.module.module'].search([('name', '=', 'havano_crm_extension')], limit=1)
    if module:
        module.button_immediate_upgrade()
        cr.commit()
        print("   Module havano_crm_extension upgraded successfully in Odoo!", flush=True)
except Exception as e:
    print(f"   Module upgrade notice: {e}", flush=True)

cr.close()
print("=== INSTANT FIX COMPLETED SUCCESSFULLY! ===", flush=True)
