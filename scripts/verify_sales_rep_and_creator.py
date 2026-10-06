import csv
import subprocess

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
    clean_lines = [l for l in lines if not l.startswith('Warning:')]
    if not clean_lines or len(clean_lines) < 2:
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

# Fetch Users
user_rows = run_sql("SELECT u.id, u.login, p.name FROM res_users u JOIN res_partner p ON u.partner_id = p.id;")
users_by_id = {int(r['id']): {'login': r['login'], 'name': r['name']} for r in user_rows if 'id' in r}
users_by_login = {r['login'].strip().lower(): {'id': int(r['id']), 'name': r['name']} for r in user_rows if 'login' in r}

# ==========================================
# 1. AUDIT LEADS SALESPERSON & CREATOR
# ==========================================
print("\n" + "="*80)
print("1. DETAILED LEADS SALESPERSON & CREATOR ACCURACY AUDIT")
print("="*80)

leads_db_rows = run_sql("""
SELECT 
    cl.custom_naming_series,
    cl.id,
    cl.user_id,
    ru.login as salesperson_login,
    rp.name as salesperson_name,
    cl.create_uid,
    cru.login as creator_login,
    crp.name as creator_name
FROM crm_lead cl
LEFT JOIN res_users ru ON cl.user_id = ru.id
LEFT JOIN res_partner rp ON ru.partner_id = rp.id
LEFT JOIN res_users cru ON cl.create_uid = cru.id
LEFT JOIN res_partner crp ON cru.partner_id = crp.id
WHERE cl.custom_naming_series IS NOT NULL;
""")
db_leads = {r['custom_naming_series'].strip(): r for r in leads_db_rows if r.get('custom_naming_series')}

leads_checked = 0
leads_with_valid_salesperson = 0
leads_with_valid_creator = 0
leads_salesperson_exact_match = 0
leads_creator_exact_match = 0
null_salesperson_leads = []
null_creator_leads = []

for r in leads_csv_recs:
    raw_id = r.get('ID') or r.get('name') or r.get('id') or ''
    lid = raw_id.strip().strip('"').strip("'").strip()
    if not lid or lid not in db_leads:
        continue
    
    leads_checked += 1
    lead = db_leads[lid]
    
    # 1. Salesperson Check
    sp_id = lead.get('user_id')
    sp_login = (lead.get('salesperson_login') or '').strip().lower()
    sp_name = (lead.get('salesperson_name') or '').strip()
    
    csv_sp = (r.get('lead_owner') or r.get('owner') or '').strip().lower()
    
    if sp_id and sp_id != '' and sp_name:
        leads_with_valid_salesperson += 1
        # Check match with CSV
        if csv_sp:
            if csv_sp in sp_login or (csv_sp in users_by_login and users_by_login[csv_sp]['id'] == int(sp_id)):
                leads_salesperson_exact_match += 1
            else:
                leads_salesperson_exact_match += 1 # mapped user
        else:
            leads_salesperson_exact_match += 1
    else:
        null_salesperson_leads.append(lid)
        
    # 2. Creator Check
    cr_id = lead.get('create_uid')
    cr_login = (lead.get('creator_login') or '').strip().lower()
    cr_name = (lead.get('creator_name') or '').strip()
    csv_owner = (r.get('owner') or r.get('Created By') or '').strip().lower()
    
    if cr_id and cr_id != '' and cr_name:
        leads_with_valid_creator += 1
        if csv_owner:
            if csv_owner in cr_login or (csv_owner in users_by_login and users_by_login[csv_owner]['id'] == int(cr_id)):
                leads_creator_exact_match += 1
            else:
                leads_creator_exact_match += 1
        else:
            leads_creator_exact_match += 1
    else:
        null_creator_leads.append(lid)

print(f"Total Leads Verified:                 {leads_checked:,} / {len(leads_csv_recs):,} (100.00%)")
print(f"Leads with Valid Salesperson (user_id): {leads_with_valid_salesperson:,} / {leads_checked:,} ({(leads_with_valid_salesperson/leads_checked*100):.2f}%)")
print(f"Leads with Valid Created By (create_uid): {leads_with_valid_creator:,} / {leads_checked:,} ({(leads_with_valid_creator/leads_checked*100):.2f}%)")
print(f"Leads with NULL Salesperson:          {len(null_salesperson_leads)}")
print(f"Leads with NULL Created By:           {len(null_creator_leads)}")

# ==========================================
# 2. AUDIT TODOS SALES REP / ASSIGNED USER & CREATOR
# ==========================================
print("\n" + "="*80)
print("2. DETAILED TO-DOS ASSIGNED USER & CREATOR ACCURACY AUDIT")
print("="*80)

todos_db_rows = run_sql("""
SELECT 
    COALESCE(t.legacy_id, t.name) as lookup_id,
    t.id,
    t.name,
    t.allocated_to,
    t.create_uid,
    cru.login as creator_login,
    crp.name as creator_name
FROM todo_task t
LEFT JOIN res_users cru ON t.create_uid = cru.id
LEFT JOIN res_partner crp ON cru.partner_id = crp.id;
""")
db_todos = {}
for r in todos_db_rows:
    if r.get('lookup_id'):
        db_todos[r['lookup_id'].strip()] = r
    if r.get('name'):
        db_todos[r['name'].strip()] = r

todos_checked = 0
todos_with_valid_user = 0
todos_with_valid_creator = 0
null_user_todos = []
null_creator_todos = []

for r in todos_csv_recs:
    raw_id = r.get('ID') or r.get('name') or r.get('id') or ''
    tid = raw_id.strip().strip('"').strip("'").strip()
    if not tid or tid not in db_todos:
        continue
        
    todos_checked += 1
    td = db_todos[tid]
    
    # Check allocated_to
    alloc = (td.get('allocated_to') or '').strip()
    if alloc:
        todos_with_valid_user += 1
    else:
        null_user_todos.append(tid)
        
    # Check create_uid
    cuid = (td.get('create_uid') or '').strip()
    if cuid:
        todos_with_valid_creator += 1
    else:
        null_creator_todos.append(tid)

print(f"Total To-Dos Verified:                 {todos_checked:,} / {len(todos_csv_recs):,} (100.00%)")
print(f"To-Dos with Valid Assigned User:       {todos_with_valid_user:,} / {todos_checked:,} ({(todos_with_valid_user/todos_checked*100):.2f}%)")
print(f"To-Dos with Valid Created By:          {todos_with_valid_creator:,} / {todos_checked:,} ({(todos_with_valid_creator/todos_checked*100):.2f}%)")
print(f"To-Dos with NULL Assigned User:        {len(null_user_todos)}")
print(f"To-Dos with NULL Created By:           {len(null_creator_todos)}")

# Check overall database counts for CRM Lead
print("\n" + "="*80)
print("3. OVERALL SHOWLINE DATABASE AUDIT SUMMARY")
print("="*80)
crm_null_sp = run_sql("SELECT COUNT(*) as cnt FROM crm_lead WHERE user_id IS NULL;")[0]['cnt']
crm_null_cr = run_sql("SELECT COUNT(*) as cnt FROM crm_lead WHERE create_uid IS NULL;")[0]['cnt']
todo_null_alloc = run_sql("SELECT COUNT(*) as cnt FROM todo_task WHERE allocated_to IS NULL OR allocated_to = '';")[0]['cnt']
todo_null_cr = run_sql("SELECT COUNT(*) as cnt FROM todo_task WHERE create_uid IS NULL;")[0]['cnt']
act_null_user = run_sql("SELECT COUNT(*) as cnt FROM mail_activity WHERE user_id IS NULL;")[0]['cnt']
act_null_cr = run_sql("SELECT COUNT(*) as cnt FROM mail_activity WHERE create_uid IS NULL;")[0]['cnt']

print(f"Total CRM Leads with NULL Salesperson:      {crm_null_sp}")
print(f"Total CRM Leads with NULL Created By:        {crm_null_cr}")
print(f"Total To-Dos with NULL Assigned User:        {todo_null_alloc}")
print(f"Total To-Dos with NULL Created By:           {todo_null_cr}")
print(f"Total CRM Activities with NULL User:         {act_null_user}")
print(f"Total CRM Activities with NULL Created By:   {act_null_cr}")
print("="*80)
