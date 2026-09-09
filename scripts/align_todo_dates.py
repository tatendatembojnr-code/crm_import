import csv, psycopg2, psycopg2.extras, re, time

def parse_frappe_template_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    headers = None
    data_start = 0
    is_template = False
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ''
        if first == 'Column Name:':
            headers = [str(c).strip() if c is not None else '' for c in row[1:]]
            data_start = i + 5
            is_template = True
            break
    if not is_template:
        headers = [str(c).strip() if c is not None else '' for c in reader[0]]
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

conn = psycopg2.connect(dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm', user='Showline', password='Showline@#$1234', host='db', port=5432)
cr = conn.cursor()

todos = parse_frappe_template_csv('/tmp/gdrive_files/file_1.csv')
updates = []
for r in todos:
    tid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    creation = clean_datetime_str(r.get('creation'))
    if tid and creation:
        updates.append((tid, creation, creation))

cr.execute('CREATE TEMP TABLE tmp_todo_dates (tid VARCHAR(255) PRIMARY KEY, cdate TIMESTAMP, legdate TIMESTAMP) ON COMMIT DROP;')
psycopg2.extras.execute_values(cr, 'INSERT INTO tmp_todo_dates (tid, cdate, legdate) VALUES %s', updates, page_size=2000)
cr.execute('UPDATE todo_task tt SET create_date = t.cdate, legacy_create_date = t.legdate FROM tmp_todo_dates t WHERE tt.legacy_id = t.tid;')
conn.commit()
print(f"Successfully aligned creation dates across all {len(updates):,} To-Dos in {time.time():.0f}!")
