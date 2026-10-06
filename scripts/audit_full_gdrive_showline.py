import csv
import psycopg2
import html
import re
from datetime import datetime

LEADS_CSV = '/tmp/audit_csvs/frappe_leads.csv'
TODOS_CSV = '/tmp/audit_csvs/frappe_todos.csv'

def parse_frappe_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    if not reader:
        return [], []
    headers = None
    data_start = 0
    is_template = False
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ""
        if first == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start = i + 5
            is_template = True
            break
    if not is_template:
        headers = [str(c).strip() if c is not None else "" for c in reader[0]]
        data_start = 1
        
    records = []
    col_offset = 1 if is_template else 0
    for row in reader[data_start:]:
        if not any(row):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            if h == '~': break
            if h and h not in row_dict:
                col = idx + col_offset
                row_dict[h] = row[col] if col < len(row) else None
        records.append(row_dict)
    return headers, records

print("Parsing CSV files...")
_, leads_recs = parse_frappe_csv(LEADS_CSV)
_, todos_recs = parse_frappe_csv(TODOS_CSV)

print(f"Total Leads in CSV: {len(leads_recs):,}")
print(f"Total To-Dos in CSV: {len(todos_recs):,}")

# Connect to Showline Database
conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='192.168.112.3',
    port=5432
)
cr = conn.cursor()

# 1. Check all users in DB
cr.execute("""
    SELECT u.id, u.login, p.name 
    FROM res_users u 
    JOIN res_partner p ON u.partner_id = p.id
""")
users_map = {r[0]: {'login': r[1], 'name': r[2]} for r in cr.fetchall()}
login_to_user_id = {u['login'].lower(): uid for uid, u in users_map.items()}

# ==========================================
# 1. COMPREHENSIVE LEADS AUDIT
# ==========================================
print("\n" + "="*80)
print("1. COMPREHENSIVE LEADS AUDIT")
print("="*80)

cr.execute("""
    SELECT 
        cl.custom_naming_series,
        cl.id,
        cl.name,
        cl.contact_name,
        cl.partner_name,
        cl.phone,
        cl.mobile,
        cl.email_from,
        cl.user_id,
        ru.login as salesperson_login,
        rp.name as salesperson_name,
        cl.create_uid,
        cru.login as creator_login,
        crp.name as creator_name,
        cl.expected_revenue,
        cl.custom_deal_size,
        cl.stage_id,
        cs.name as stage_name,
        cl.city,
        cl.street,
        cl.crm_product_id,
        cp.name as product_name
    FROM crm_lead cl
    LEFT JOIN res_users ru ON cl.user_id = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id
    LEFT JOIN res_users cru ON cl.create_uid = cru.id
    LEFT JOIN res_partner crp ON cru.partner_id = crp.id
    LEFT JOIN crm_stage cs ON cl.stage_id = cs.id
    LEFT JOIN crm_product cp ON cl.crm_product_id = cp.id
    WHERE cl.custom_naming_series IS NOT NULL
""")
db_leads_rows = cr.fetchall()
db_leads = {}
for r in db_leads_rows:
    db_leads[r[0]] = {
        'id': r[1],
        'name': r[2],
        'contact_name': r[3],
        'partner_name': r[4],
        'phone': r[5],
        'mobile': r[6],
        'email': r[7],
        'user_id': r[8],
        'salesperson_login': r[9],
        'salesperson_name': r[10],
        'create_uid': r[11],
        'creator_login': r[12],
        'creator_name': r[13],
        'expected_revenue': r[14],
        'deal_size': r[15],
        'stage_id': r[16],
        'stage_name': r[17],
        'city': r[18],
        'street': r[19],
        'crm_product_id': r[20],
        'product_name': r[21]
    }

total_csv_leads = len(leads_recs)
total_db_leads = len(db_leads)
matched_leads = 0
leads_with_salesperson = 0
leads_null_salesperson = 0
leads_with_creator = 0
leads_with_contact_name = 0
leads_with_phone = 0
leads_with_email = 0
leads_with_product = 0
leads_with_revenue = 0

missing_leads = []

for r in leads_recs:
    lid = (r.get('ID') or r.get('name') or r.get('id') or '').strip().strip('"')
    if not lid: continue
    if lid in db_leads:
        matched_leads += 1
        lead = db_leads[lid]
        if lead['user_id']:
            leads_with_salesperson += 1
        else:
            leads_null_salesperson += 1
        if lead['create_uid']:
            leads_with_creator += 1
        if lead['contact_name'] and lead['contact_name'].strip():
            leads_with_contact_name += 1
        if lead['phone'] or lead['mobile']:
            leads_with_phone += 1
        if lead['email']:
            leads_with_email += 1
        if lead['crm_product_id'] or lead['product_name']:
            leads_with_product += 1
        if lead['expected_revenue'] or lead['deal_size']:
            leads_with_revenue += 1
    else:
        missing_leads.append(lid)

# Also check overall crm_lead counts
cr.execute("SELECT COUNT(*), COUNT(user_id), COUNT(create_uid) FROM crm_lead")
tot_all_crm, tot_all_salesperson, tot_all_creator = cr.fetchone()

print(f"Total Leads in CSV:                 {total_csv_leads:,}")
print(f"Total Leads in Database (Overall):  {tot_all_crm:,}")
print(f"Total Imported Leads in Database:   {total_db_leads:,}")
print(f"Matched CSV Leads to Database:      {matched_leads:,} / {total_csv_leads:,} ({(matched_leads/total_csv_leads*100):.2f}%)")
print(f"Leads with Salesperson Assigned:    {leads_with_salesperson:,} / {matched_leads:,} ({(leads_with_salesperson/matched_leads*100):.2f}%)")
print(f"Leads with NULL Salesperson:        {leads_null_salesperson:,}")
print(f"Leads with Created By User:         {leads_with_creator:,} / {matched_leads:,} ({(leads_with_creator/matched_leads*100):.2f}%)")
print(f"Leads with Contact Name:            {leads_with_contact_name:,} / {matched_leads:,} ({(leads_with_contact_name/matched_leads*100):.2f}%)")
print(f"Leads with Phone/Mobile:            {leads_with_phone:,} / {matched_leads:,} ({(leads_with_phone/matched_leads*100):.2f}%)")
print(f"Leads with Email:                   {leads_with_email:,} / {matched_leads:,} ({(leads_with_email/matched_leads*100):.2f}%)")
print(f"Leads with Product Interest:        {leads_with_product:,} / {matched_leads:,} ({(leads_with_product/matched_leads*100):.2f}%)")
print(f"Leads with Deal Size / Revenue:     {leads_with_revenue:,} / {matched_leads:,} ({(leads_with_revenue/matched_leads*100):.2f}%)")

if missing_leads:
    print(f"⚠️ Missing Leads ({len(missing_leads)}): {missing_leads[:10]}")
else:
    print("✓ 100% of all Leads from the CSV exist in Odoo!")

# Salesperson Breakdown
print("\n--- Salesperson Breakdown in Odoo CRM Leads ---")
cr.execute("""
    SELECT COALESCE(rp.name, 'Unassigned') as sp_name, COUNT(*) 
    FROM crm_lead cl
    LEFT JOIN res_users ru ON cl.user_id = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id
    GROUP BY rp.name
    ORDER BY COUNT(*) DESC
""")
for sp_name, cnt in cr.fetchall():
    print(f"  {sp_name}: {cnt:,} leads")

# ==========================================
# 2. COMPREHENSIVE TO-DOS & ACTIVITIES AUDIT
# ==========================================
print("\n" + "="*80)
print("2. COMPREHENSIVE TO-DOS & ACTIVITIES AUDIT")
print("="*80)

cr.execute("""
    SELECT 
        COALESCE(t.legacy_id, t.name) as lookup_id,
        t.id,
        t.name,
        t.status,
        t.allocated_to,
        t.lead_id,
        t.date,
        t.create_date,
        t.create_uid,
        cl.custom_naming_series,
        rp.name as allocated_user_name,
        ru.login as allocated_user_login
    FROM todo_task t
    LEFT JOIN crm_lead cl ON t.lead_id = cl.id
    LEFT JOIN res_users ru ON t.allocated_to = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id
""")
db_todos_rows = cr.fetchall()
db_todos = {}
for r in db_todos_rows:
    if r[0]:
        db_todos[r[0]] = {
            'id': r[1],
            'name': r[2],
            'status': r[3],
            'allocated_to': r[4],
            'lead_id': r[5],
            'date': r[6],
            'create_date': r[7],
            'create_uid': r[8],
            'lead_series': r[9],
            'user_name': r[10],
            'user_login': r[11]
        }

cr.execute("SELECT COUNT(*) FROM todo_task")
tot_all_todos = cr.fetchone()[0]

cr.execute("SELECT COUNT(*) FROM mail_activity WHERE res_model = 'crm.lead'")
tot_crm_activities = cr.fetchone()[0]

cr.execute("SELECT COUNT(*) FROM mail_activity")
tot_all_activities = cr.fetchone()[0]

matched_todos = 0
todos_with_user = 0
todos_linked_to_lead = 0
missing_todos = []

for r in todos_recs:
    tid = (r.get('ID') or r.get('name') or r.get('id') or '').strip().strip('"')
    if not tid: continue
    if tid in db_todos:
        matched_todos += 1
        td = db_todos[tid]
        if td['allocated_to'] or td['user_name']:
            todos_with_user += 1
        if td['lead_id']:
            todos_linked_to_lead += 1
    else:
        missing_todos.append(tid)

print(f"Total To-Dos in CSV:                {len(todos_recs):,}")
print(f"Total To-Dos in Database:           {tot_all_todos:,}")
print(f"Matched CSV To-Dos to Database:     {matched_todos:,} / {len(todos_recs):,} ({(matched_todos/len(todos_recs)*100):.2f}%)")
print(f"To-Dos with Assigned User:          {todos_with_user:,} / {matched_todos:,} ({(todos_with_user/matched_todos*100):.2f}%)")
print(f"To-Dos Linked to CRM Lead:          {todos_linked_to_lead:,} / {matched_todos:,} ({(todos_linked_to_lead/matched_todos*100):.2f}%)")
print(f"Total CRM Mail Activities in DB:    {tot_crm_activities:,}")
print(f"Total Mail Activities (Overall):    {tot_all_activities:,}")

if missing_todos:
    print(f"⚠️ Missing To-Dos ({len(missing_todos)}): {missing_todos[:10]}")
else:
    print("✓ 100% of all To-Dos from the CSV exist in Odoo!")

# To-Do User Breakdown
print("\n--- To-Do Assigned User Breakdown ---")
cr.execute("""
    SELECT COALESCE(rp.name, 'Unassigned') as user_name, COUNT(*) 
    FROM todo_task t
    LEFT JOIN res_users ru ON t.allocated_to = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id
    GROUP BY rp.name
    ORDER BY COUNT(*) DESC
""")
for uname, cnt in cr.fetchall():
    print(f"  {uname}: {cnt:,} to-dos")

print("\n" + "="*80)
print("AUDIT COMPLETE")
print("="*80)
