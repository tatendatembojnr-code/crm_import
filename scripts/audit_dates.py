import csv
import psycopg2
import re

def parse_frappe_template_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
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
        if not any(row): continue
        row_dict = {}
        for idx, h in enumerate(headers):
            if h == '~': break
            if h and h not in row_dict:
                col = idx + col_offset
                row_dict[h] = row[col] if col < len(row) else None
        records.append(row_dict)
    return records

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

leads_gdrive = parse_frappe_template_csv('/tmp/gdrive_files/file_3.csv')
todos_gdrive = parse_frappe_template_csv('/tmp/gdrive_files/file_1.csv')

print("="*80)
print("=== DEEP-DIVE DATE AUDIT: CSV VS LIVE DATABASE ===")
print("="*80)

# --- LEAD DATES AUDIT ---
cr.execute("""
    SELECT 
        custom_naming_series,
        create_date,
        legacy_create_date,
        custom_quote_date,
        custom_proposal_date
    FROM crm_lead
    WHERE custom_naming_series IS NOT NULL
""")
db_leads = {r[0]: {'create_date': str(r[1]) if r[1] else '', 'legacy_create_date': str(r[2]) if r[2] else '', 'custom_quote_date': str(r[3]) if r[3] else '', 'custom_proposal_date': str(r[4]) if r[4] else ''} for r in cr.fetchall() if r[0]}

print("\n--- SAMPLE 10 LEADS DATE AUDIT (CSV VS ODOO DB) ---")
count = 0
lead_create_matches = 0
lead_create_total_with_date = 0
lead_quote_matches = 0
lead_quote_total = 0

for r in leads_gdrive:
    lid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    if not lid or lid not in db_leads: continue
    
    csv_creation = (r.get('creation') or r.get('Qualified on') or r.get('Added On (Notes)') or '').strip()
    csv_quote = (r.get('Quote Date') or r.get('custom_quote_date') or '').strip()
    
    db_rec = db_leads[lid]
    db_create = db_rec['create_date'][:10]
    db_leg = db_rec['legacy_create_date'][:10]
    db_quote = db_rec['custom_quote_date'][:10]
    
    if csv_creation:
        lead_create_total_with_date += 1
        csv_c_d = csv_creation[:10]
        if csv_c_d == db_create or csv_c_d == db_leg:
            lead_create_matches += 1
            
    if csv_quote:
        lead_quote_total += 1
        q_parts = re.split(r'[-/]', csv_quote.split(' ')[0])
        norm_q = ""
        if len(q_parts) == 3:
            if len(q_parts[0]) == 4: norm_q = f"{q_parts[0]}-{q_parts[1].zfill(2)}-{q_parts[2].zfill(2)}"
            elif len(q_parts[2]) == 4: norm_q = f"{q_parts[2]}-{q_parts[1].zfill(2)}-{q_parts[0].zfill(2)}"
        if norm_q and norm_q == db_quote:
            lead_quote_matches += 1
            
    if count < 10 and (csv_creation or csv_quote):
        count += 1
        print(f"Lead [{lid}]:")
        print(f"  • CSV Creation Date:   '{csv_creation}'  -->  DB create_date: '{db_create}', legacy: '{db_leg}'")
        if csv_quote or db_quote:
            print(f"  • CSV Quote Date:      '{csv_quote}'  -->  DB quote_date:  '{db_quote}'")

print(f"\nLead Dates Summary:")
print(f"  • Leads with Creation Date in CSV: {lead_create_total_with_date:,}")
print(f"  • Matching DB Creation Dates:      {lead_create_matches:,}")
print(f"  • Quote Dates in CSV:              {lead_quote_total:,}")
print(f"  • Matching DB Quote Dates:         {lead_quote_matches:,}")

# --- TODO DATES AUDIT ---
cr.execute("""
    SELECT 
        COALESCE(legacy_id, name) as lookup_id,
        date,
        create_date,
        legacy_create_date
    FROM todo_task
""")
db_todos = {r[0]: {'date': str(r[1]) if r[1] else '', 'create_date': str(r[2]) if r[2] else '', 'legacy_create_date': str(r[3]) if r[3] else ''} for r in cr.fetchall() if r[0]}

print("\n--- SAMPLE 10 TO-DOS DATE AUDIT (CSV VS ODOO DB) ---")
count = 0
todo_due_matches = 0
todo_due_total = 0
todo_create_matches = 0
todo_create_total = 0

for r in todos_gdrive:
    tid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    if not tid or tid not in db_todos: continue
    
    csv_due = (r.get('date') or r.get('Due Date') or '').strip()
    csv_creation = (r.get('creation') or '').strip()
    
    db_rec = db_todos[tid]
    db_due = db_rec['date'][:10]
    db_create = db_rec['create_date'][:10]
    db_leg = db_rec['legacy_create_date'][:10]
    
    if csv_due:
        todo_due_total += 1
        # Normalize DD-MM-YYYY or YYYY-MM-DD
        c_parts = re.split(r'[-/]', csv_due.split(' ')[0])
        norm_c = ""
        if len(c_parts) == 3:
            if len(c_parts[0]) == 4: norm_c = f"{c_parts[0]}-{c_parts[1].zfill(2)}-{c_parts[2].zfill(2)}"
            elif len(c_parts[2]) == 4: norm_c = f"{c_parts[2]}-{c_parts[1].zfill(2)}-{c_parts[0].zfill(2)}"
        if norm_c and norm_c == db_due:
            todo_due_matches += 1
            
    if csv_creation:
        todo_create_total += 1
        c_parts = re.split(r'[-/]', csv_creation.split(' ')[0])
        norm_c = ""
        if len(c_parts) == 3:
            if len(c_parts[0]) == 4: norm_c = f"{c_parts[0]}-{c_parts[1].zfill(2)}-{c_parts[2].zfill(2)}"
            elif len(c_parts[2]) == 4: norm_c = f"{c_parts[2]}-{c_parts[1].zfill(2)}-{c_parts[0].zfill(2)}"
        if norm_c and (norm_c == db_create or norm_c == db_leg):
            todo_create_matches += 1
            
    if count < 10 and (csv_due or csv_creation):
        count += 1
        print(f"ToDo [{tid}]:")
        print(f"  • CSV Due Date:      '{csv_due}'  -->  DB date:        '{db_due}'")
        print(f"  • CSV Creation Date:  '{csv_creation}'  -->  DB create_date: '{db_create}', legacy: '{db_leg}'")

print(f"\nTo-Dos Dates Summary:")
print(f"  • To-Dos with Due Date in CSV:     {todo_due_total:,}")
print(f"  • Matching DB Due Dates:           {todo_due_matches:,}")
print(f"  • To-Dos with Creation in CSV:     {todo_create_total:,}")
print(f"  • Matching DB Creation Dates:      {todo_create_matches:,}")
print("="*80)
