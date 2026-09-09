import csv
import psycopg2
import psycopg2.extras
import re
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

def clean_date_str(val):
    if not val: return None
    s = str(val).strip().split(' ')[0]
    parts = re.split(r'[-/]', s)
    if len(parts) == 3:
        if len(parts[0]) == 4: return f"{parts[0]}-{parts[1].zfill(2)}-{parts[2].zfill(2)}"
        elif len(parts[2]) == 4: return f"{parts[2]}-{parts[1].zfill(2)}-{parts[0].zfill(2)}"
    return None

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

leads_gdrive = parse_frappe_template_csv('/tmp/gdrive_files/file_3.csv')
print(f"Aligning dates for {len(leads_gdrive):,} leads from Google Drive CSV...")

date_updates = []
for r in leads_gdrive:
    lid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    if not lid: continue
    
    creation_raw = (r.get('creation') or r.get('Qualified on') or r.get('Added On (Notes)') or '').strip()
    creation_dt = clean_datetime_str(creation_raw)
    
    quote_raw = (r.get('Quote Date') or r.get('custom_quote_date') or '').strip()
    quote_d = clean_date_str(quote_raw)
    
    date_updates.append((lid, creation_dt, creation_dt, quote_d))

start = time.time()
# Fast bulk update using temporary table
cr.execute("""
    CREATE TEMP TABLE tmp_lead_dates (
        lid VARCHAR(255) PRIMARY KEY,
        cdate TIMESTAMP,
        legdate TIMESTAMP,
        qdate DATE
    ) ON COMMIT DROP;
""")

psycopg2.extras.execute_values(
    cr,
    "INSERT INTO tmp_lead_dates (lid, cdate, legdate, qdate) VALUES %s",
    date_updates,
    page_size=2000
)

cr.execute("""
    UPDATE crm_lead cl
    SET 
        create_date = COALESCE(t.cdate, cl.create_date),
        legacy_create_date = COALESCE(t.legdate, cl.legacy_create_date),
        custom_quote_date = COALESCE(t.qdate, cl.custom_quote_date)
    FROM tmp_lead_dates t
    WHERE cl.custom_naming_series = t.lid;
""")
conn.commit()
print(f"Bulk date alignment finished in {time.time()-start:.2f} seconds!")
