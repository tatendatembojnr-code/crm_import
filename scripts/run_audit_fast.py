import csv
import subprocess
import json
import os
import sys

LEADS_CSV = '/tmp/audit_csvs/frappe_leads.csv'
TODOS_CSV = '/tmp/audit_csvs/frappe_todos.csv'

def run_sql(query):
    ssh_cmd = [
        "sshpass", "-p", "Farai@#$1234", "ssh", "-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=/dev/null",
        "root@127.0.0.1",
        f"docker exec -i psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -A -F '\t' -c \"{query}\""
    ]
    res = subprocess.run(ssh_cmd, capture_output=True, text=True)
    if res.returncode != 0:
        print("SQL Error:", res.stderr)
        return []
    lines = res.stdout.strip().split('\n')
    if not lines or len(lines) < 2:
        return []
    # Filter out ssh warnings
    clean_lines = [l for l in lines if not l.startswith('Warning:')]
    if not clean_lines:
        return []
    headers = clean_lines[0].split('\t')
    rows = []
    for l in clean_lines[1:]:
        if l.endswith(' rows)') or l.endswith(' row)') or l.startswith('('):
            continue
        parts = l.split('\t')
        if len(parts) == len(headers):
            rows.append(dict(zip(headers, parts)))
    return rows

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
_, leads_csv_recs = parse_frappe_csv(LEADS_CSV)
_, todos_csv_recs = parse_frappe_csv(TODOS_CSV)

print(f"Total Leads in CSV:  {len(leads_csv_recs):,}")
print(f"Total To-Dos in CSV: {len(todos_csv_recs):,}")

print("\nFetching Database Records...")

# 1. Fetch Users
user_rows = run_sql("SELECT u.id, u.login, p.name FROM res_users u JOIN res_partner p ON u.partner_id = p.id;")
users_map = {int(r['id']): {'login': r['login'], 'name': r['name']} for r in user_rows if 'id' in r}
print(f"Fetched {len(users_map)} system users.")

# 2. Fetch Leads
print("Fetching CRM Leads from DB...")
leads_sql = """
SELECT 
    cl.custom_naming_series,
    cl.id,
    REPLACE(cl.name, E'\t', ' ') as name,
    REPLACE(cl.contact_name, E'\t', ' ') as contact_name,
    REPLACE(cl.partner_name, E'\t', ' ') as partner_name,
    cl.phone,
    cl.email_from,
    cl.user_id,
    rp.name as salesperson_name,
    cl.create_uid,
    crp.name as creator_name,
    cl.expected_revenue,
    cl.custom_deal_size,
    cl.crm_product_id,
    cp.name as product_name,
    cl.city,
    cl.street
FROM crm_lead cl
LEFT JOIN res_users ru ON cl.user_id = ru.id
LEFT JOIN res_partner rp ON ru.partner_id = rp.id
LEFT JOIN res_users cru ON cl.create_uid = cru.id
LEFT JOIN res_partner crp ON cru.partner_id = crp.id
LEFT JOIN crm_product cp ON cl.crm_product_id = cp.id
WHERE cl.custom_naming_series IS NOT NULL;
"""
db_leads_rows = run_sql(leads_sql)
db_leads = {}
for r in db_leads_rows:
    if 'custom_naming_series' in r and r['custom_naming_series']:
        db_leads[r['custom_naming_series'].strip()] = r
    if 'name' in r and r['name']:
        db_leads[r['name'].strip()] = r
print(f"Fetched {len(db_leads):,} imported leads from database.")

# 3. Fetch To-Dos
print("Fetching To-Dos from DB...")
todos_sql = """
SELECT 
    COALESCE(t.legacy_id, t.name) as lookup_id,
    t.id,
    t.name,
    t.status,
    t.allocated_to,
    t.lead_id,
    t.date,
    t.reference_name
FROM todo_task t;
"""
db_todos_rows = run_sql(todos_sql)
db_todos = {}
for r in db_todos_rows:
    if 'lookup_id' in r and r['lookup_id']:
        db_todos[r['lookup_id'].strip()] = r
    if 'name' in r and r['name']:
        db_todos[r['name'].strip()] = r
print(f"Fetched {len(db_todos):,} to-dos from database.")

# ==========================================
# LEADS AUDIT
# ==========================================
print("\n" + "="*80)
print("LEADS ACCURACY & COMPLETENESS REPORT")
print("="*80)

total_csv_leads = len(leads_csv_recs)
matched_leads = 0
leads_with_salesperson = 0
leads_null_salesperson = 0
leads_with_creator = 0
leads_with_contact_name = 0
leads_with_partner_name = 0
leads_with_phone = 0
leads_with_email = 0
leads_with_product = 0
leads_with_revenue = 0
leads_with_address = 0
missing_leads = []

for r in leads_csv_recs:
    raw_id = r.get('ID') or r.get('name') or r.get('id') or ''
    lid = raw_id.strip().strip('"').strip("'").strip()
    if not lid: continue
    if lid in db_leads:
        matched_leads += 1
        lead = db_leads[lid]
        
        # Salesperson
        if lead.get('user_id') and lead['user_id'].strip():
            leads_with_salesperson += 1
        else:
            leads_null_salesperson += 1
            
        # Creator
        if lead.get('create_uid') and lead['create_uid'].strip():
            leads_with_creator += 1
            
        # Contact Name
        if lead.get('contact_name') and lead['contact_name'].strip():
            leads_with_contact_name += 1
            
        # Organization / Partner Name
        if lead.get('partner_name') and lead['partner_name'].strip():
            leads_with_partner_name += 1
            
        # Phone
        if lead.get('phone') and lead['phone'].strip():
            leads_with_phone += 1
            
        # Email
        if lead.get('email_from') and lead['email_from'].strip():
            leads_with_email += 1
            
        # Product
        if lead.get('crm_product_id') or lead.get('product_name'):
            leads_with_product += 1
            
        # Revenue / Deal Size
        if lead.get('expected_revenue') or lead.get('custom_deal_size'):
            leads_with_revenue += 1
            
        # Address / City
        if lead.get('city') or lead.get('street'):
            leads_with_address += 1
    else:
        missing_leads.append(lid)

print(f"Total Leads in CSV:                      {total_csv_leads:,}")
print(f"Matched Leads in Database:               {matched_leads:,} / {total_csv_leads:,} ({(matched_leads/total_csv_leads*100):.2f}%)")
print(f"Leads with Salesperson Assigned:         {leads_with_salesperson:,} / {matched_leads:,} ({(leads_with_salesperson/matched_leads*100):.2f}%)")
print(f"Leads with NULL Salesperson:             {leads_null_salesperson:,}")
print(f"Leads with Created By User:              {leads_with_creator:,} / {matched_leads:,} ({(leads_with_creator/matched_leads*100):.2f}%)")
print(f"Leads with Contact Name:                 {leads_with_contact_name:,} / {matched_leads:,} ({(leads_with_contact_name/matched_leads*100):.2f}%)")
print(f"Leads with Organization / Store Name:    {leads_with_partner_name:,} / {matched_leads:,} ({(leads_with_partner_name/matched_leads*100):.2f}%)")
print(f"Leads with Phone:                        {leads_with_phone:,} / {matched_leads:,} ({(leads_with_phone/matched_leads*100):.2f}%)")
print(f"Leads with Email:                        {leads_with_email:,} / {matched_leads:,} ({(leads_with_email/matched_leads*100):.2f}%)")
print(f"Leads with Product Interest:             {leads_with_product:,} / {matched_leads:,} ({(leads_with_product/matched_leads*100):.2f}%)")
print(f"Leads with Expected Revenue / Deal Size: {leads_with_revenue:,} / {matched_leads:,} ({(leads_with_revenue/matched_leads*100):.2f}%)")
print(f"Leads with City / Address:               {leads_with_address:,} / {matched_leads:,} ({(leads_with_address/matched_leads*100):.2f}%)")

if missing_leads:
    print(f"⚠️ Missing Leads ({len(missing_leads)}): {missing_leads[:10]}")
else:
    print("✓ VERIFIED: 100% of all Leads from the CSV are present in the Odoo database!")

# ==========================================
# TO-DOS & ACTIVITIES AUDIT
# ==========================================
print("\n" + "="*80)
print("TO-DOS & ACTIVITIES ACCURACY & COMPLETENESS REPORT")
print("="*80)

total_csv_todos = len(todos_csv_recs)
matched_todos = 0
todos_with_user = 0
todos_linked_to_lead = 0
missing_todos = []

for r in todos_csv_recs:
    tid = (r.get('ID') or r.get('name') or r.get('id') or '').strip().strip('"')
    if not tid: continue
    if tid in db_todos:
        matched_todos += 1
        td = db_todos[tid]
        if td.get('allocated_to') and td['allocated_to'].strip():
            todos_with_user += 1
        if td.get('lead_id') and td['lead_id'].strip():
            todos_linked_to_lead += 1
    else:
        missing_todos.append(tid)

# Get activities count
act_rows = run_sql("SELECT count(*) as cnt FROM mail_activity WHERE res_model = 'crm.lead';")
crm_activities_count = act_rows[0]['cnt'] if act_rows else 'N/A'

all_act_rows = run_sql("SELECT count(*) as cnt FROM mail_activity;")
total_activities_count = all_act_rows[0]['cnt'] if all_act_rows else 'N/A'

print(f"Total To-Dos in CSV:                     {total_csv_todos:,}")
print(f"Matched To-Dos in Database:              {matched_todos:,} / {total_csv_todos:,} ({(matched_todos/total_csv_todos*100):.2f}%)")
print(f"To-Dos with Assigned User:               {todos_with_user:,} / {matched_todos:,} ({(todos_with_user/matched_todos*100):.2f}%)")
print(f"To-Dos Linked to CRM Leads:              {todos_linked_to_lead:,} / {matched_todos:,} ({(todos_linked_to_lead/matched_todos*100):.2f}%)")
print(f"Active CRM Mail Activities in Odoo:      {crm_activities_count}")
print(f"Total Mail Activities across Odoo:       {total_activities_count}")

if missing_todos:
    print(f"⚠️ Missing To-Dos ({len(missing_todos)}): {missing_todos[:10]}")
else:
    print("✓ VERIFIED: 100% of all To-Dos from the CSV are present in the Odoo database!")

# ==========================================
# SALESPERSON BREAKDOWN
# ==========================================
print("\n" + "="*80)
print("SALESPERSON BREAKDOWN IN SHOWLINE ODOO")
print("="*80)
sp_rows = run_sql("""
SELECT COALESCE(rp.name, 'Unassigned') as sp_name, COUNT(*) as cnt 
FROM crm_lead cl
LEFT JOIN res_users ru ON cl.user_id = ru.id
LEFT JOIN res_partner rp ON ru.partner_id = rp.id
GROUP BY rp.name
ORDER BY COUNT(*) DESC;
""")
for r in sp_rows:
    print(f"  {r['sp_name']}: {int(r['cnt']):,} leads")

print("\n" + "="*80)
print("AUDIT VERIFICATION COMPLETED SUCCESSFULLY")
print("="*80)
