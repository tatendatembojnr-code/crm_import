import csv
import psycopg2

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
    return headers, records

headers, records = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')
print("Total records:", len(records))
print("\n--- ALL CSV HEADERS ---")
for idx, h in enumerate(headers):
    print(f"{idx}: {h}")

# Search for BYD Steel Structures or Lead014995
print("\n--- SEARCH FOR BYD STEEL STRUCTURES ---")
for r in records:
    name = str(r.get('Lead Name') or r.get('lead_name') or r.get('organization_lead') or r.get('company_name') or '')
    lid = str(r.get('ID') or r.get('name') or '')
    if 'BYD' in name or 'BYD' in lid or 'Lead014995' in lid:
        print(f"Match: ID={lid}, Name={name}")
        for k, v in r.items():
            if v:
                print(f"  {k}: {repr(v)}")

# Connect to DB and inspect crm_lead columns & sample record
conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()
cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='crm_lead' AND (column_name LIKE '%note%' OR column_name LIKE '%desc%' OR column_name LIKE '%street%' OR column_name LIKE '%address%');")
print("\n--- CRM_LEAD COLUMNS ---")
for col in cr.fetchall():
    print(col)

cr.execute("SELECT id, name, custom_naming_series, street, street2, city, description, contact_name FROM crm_lead WHERE id=78626 OR custom_naming_series='Lead014995';")
print("\n--- DB RECORD FOR 78626 / Lead014995 ---")
for r in cr.fetchall():
    print(r)

