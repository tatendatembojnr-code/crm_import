import csv, psycopg2, psycopg2.extras

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

def safe_float(val):
    if not val: return 0.0
    try:
        s = str(val).replace(',', '').replace('$', '').strip().strip('"')
        return float(s)
    except:
        return 0.0

conn = psycopg2.connect(dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm', user='Showline', password='Showline@#$1234', host='db', port=5432)
cr = conn.cursor()

leads = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')
updates = []
for r in leads:
    lid = (r.get('ID') or r.get('name') or '').strip().strip('"')
    amt = safe_float(r.get('Deal Size $') or r.get('custom_deal_size_') or r.get('Deal size'))
    if lid:
        updates.append((lid, amt, amt))

cr.execute('CREATE TEMP TABLE tmp_lead_amts (lid VARCHAR(255) PRIMARY KEY, exp_rev NUMERIC, dsize NUMERIC) ON COMMIT DROP;')
psycopg2.extras.execute_values(cr, 'INSERT INTO tmp_lead_amts (lid, exp_rev, dsize) VALUES %s', updates, page_size=2000)
cr.execute('UPDATE crm_lead cl SET expected_revenue = t.exp_rev, custom_deal_size = t.dsize FROM tmp_lead_amts t WHERE cl.custom_naming_series = t.lid;')
conn.commit()
print(f"Successfully synced exact deal sizes for all {len(updates):,} leads!")
