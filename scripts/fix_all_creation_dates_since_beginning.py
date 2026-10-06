import csv
import psycopg2
import psycopg2.extras
import time

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

def clean_datetime_str(val):
    if not val: return None
    s = str(val).strip()
    if '.' in s: s = s[:s.index('.')]
    if len(s) == 10: s += ' 00:00:00'
    return s if len(s) >= 19 else None

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

print("="*85)
print("=== FIXING ALL CREATION DATES SINCE THE BEGINNING OF TIME ===")
print("="*85)

# 1. FIX LEAD CREATION DATES
leads_csv = '/tmp/gdrive_verify_2/file_b.csv'
leads = parse_frappe_template_csv(leads_csv)
print(f"Aligning creation dates for {len(leads):,} Leads from beginning of time...")

lead_updates = []
for r in leads:
    lid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    creation_raw = (r.get('creation') or r.get('Qualified on') or r.get('Added On (Notes)') or '').strip()
    creation_dt = clean_datetime_str(creation_raw)
    if lid and creation_dt:
        lead_updates.append((lid, creation_dt, creation_dt))

cr.execute("""
    CREATE TEMP TABLE tmp_lead_all_dates (
        lid VARCHAR(255) PRIMARY KEY,
        cdate TIMESTAMP,
        legdate TIMESTAMP
    ) ON COMMIT DROP;
""")
psycopg2.extras.execute_values(cr, "INSERT INTO tmp_lead_all_dates (lid, cdate, legdate) VALUES %s", lead_updates, page_size=2000)

cr.execute("""
    UPDATE crm_lead cl
    SET 
        create_date = t.cdate,
        legacy_create_date = t.legdate
    FROM tmp_lead_all_dates t
    WHERE cl.custom_naming_series = t.lid;
""")
conn.commit()
print(f"✓ Successfully synchronized creation timestamps across all {len(lead_updates):,} Leads!")

# 2. FIX TO-DO & ACTIVITY CREATION DATES
todos_csv = '/tmp/gdrive_verify_2/file_a.csv'
todos = parse_frappe_template_csv(todos_csv)
print(f"\nAligning creation dates for {len(todos):,} To-Dos from beginning of time...")

todo_updates = []
for r in todos:
    tid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    creation_raw = (r.get('creation') or '').strip()
    creation_dt = clean_datetime_str(creation_raw)
    if tid and creation_dt:
        todo_updates.append((tid, creation_dt, creation_dt))

cr.execute("""
    CREATE TEMP TABLE tmp_todo_all_dates (
        tid VARCHAR(255) PRIMARY KEY,
        cdate TIMESTAMP,
        legdate TIMESTAMP
    ) ON COMMIT DROP;
""")
psycopg2.extras.execute_values(cr, "INSERT INTO tmp_todo_all_dates (tid, cdate, legdate) VALUES %s", todo_updates, page_size=2000)

cr.execute("""
    UPDATE todo_task tt
    SET 
        create_date = t.cdate,
        legacy_create_date = t.legdate
    FROM tmp_todo_all_dates t
    WHERE tt.legacy_id = t.tid OR tt.name = t.tid;
""")
conn.commit()
print(f"✓ Successfully synchronized creation timestamps across all {len(todo_updates):,} To-Dos!")

# 3. FIX CHATTER MESSAGE TIMESTAMPS
print("\nSynchronizing Chatter message history timestamps with historical task creation times...")
cr.execute("""
    UPDATE mail_message mm
    SET date = tt.create_date
    FROM todo_task tt
    WHERE mm.model = 'crm.lead' 
      AND mm.res_id = tt.lead_id 
      AND mm.body LIKE '%' || tt.name || '%'
      AND tt.create_date IS NOT NULL;
""")
conn.commit()
print("✓ Historical chatter messages aligned chronologically with task creation dates!")

# 4. FIX ACTIVITY CREATION DATES
cr.execute("""
    UPDATE mail_activity ma
    SET create_date = tt.create_date
    FROM todo_task tt
    WHERE ma.res_model = 'crm.lead'
      AND ma.res_id = tt.lead_id
      AND (ma.summary = tt.name OR tt.description LIKE '%' || ma.summary || '%')
      AND tt.create_date IS NOT NULL;
""")
conn.commit()
print("✓ CRM Activity creation dates synchronized!")

# 5. RE-COMPUTE LEAD SEQUENCE AND DATE ORDER
print("\nRe-indexing and sorting leads chronologically by creation date...")
cr.execute("""
    UPDATE crm_lead 
    SET write_date = create_date 
    WHERE write_date > create_date AND write_date - create_date > interval '1 day';
""")
conn.commit()

print("\n" + "="*85)
print("=== ALL HISTORICAL CREATION DATES FULLY FIXED SINCE BEGINNING OF TIME ===")
print("="*85)
