import csv
import psycopg2
import psycopg2.extras

print("="*80)
print("=== CONVERTING & SYNCHRONIZING DEMO DONE VALUES ===")
print("="*80)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# 1. Alter custom_demo_done column type in PostgreSQL if needed
cr.execute("""
    SELECT data_type FROM information_schema.columns 
    WHERE table_name='crm_lead' AND column_name='custom_demo_done';
""")
dt = cr.fetchone()[0]
print(f"Current custom_demo_done data type: {dt}")

if dt == 'boolean':
    cr.execute("""
        ALTER TABLE crm_lead 
        ALTER COLUMN custom_demo_done TYPE VARCHAR(20) 
        USING (CASE WHEN custom_demo_done IS TRUE THEN 'yes' ELSE 'no' END);
    """)
    conn.commit()
    print("✓ Successfully converted custom_demo_done column to VARCHAR(20)")

# 2. Parse demo values from file_b.csv
def parse_frappe_template_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    headers = [str(c).strip() if c is not None else "" for c in reader[0]]
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ""
        if first == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start = i + 5
            return headers, reader[data_start:]
    return headers, reader[1:]

headers, rows = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')

name_idx = None
d1_idx = None
d2_idx = None

for idx, h in enumerate(headers):
    if h == '~': break
    if h in ['name', 'ID'] and name_idx is None: name_idx = idx + 1
    if h == 'custom_demo_done_' and d1_idx is None: d1_idx = idx + 1
    if h == 'custom_demo_done_online_or_onsite' and d2_idx is None: d2_idx = idx + 1

demo_updates = []
for r in rows:
    if not any(r): continue
    lid = r[name_idx].strip().strip('"') if name_idx is not None and len(r) > name_idx else None
    if not lid: continue
    
    raw_d1 = str(r[d1_idx] if d1_idx is not None and len(r) > d1_idx else '').strip().lower()
    raw_d2 = str(r[d2_idx] if d2_idx is not None and len(r) > d2_idx else '').strip()
    
    demo_done = 'yes' if 'demo' in raw_d1 and 'no' not in raw_d1 else ('yes' if raw_d1 == 'yes' else 'no')
    demo_type = 'Onsite' if 'onsite' in raw_d2.lower() else ('Online' if 'online' in raw_d2.lower() else 'N/A')
    
    demo_updates.append((lid, demo_done, demo_type))

print(f"Total leads prepared for demo sync: {len(demo_updates):,}")
yes_count = sum(1 for d in demo_updates if d[1] == 'yes')
print(f"  • Demo Done = 'yes': {yes_count:,}")
print(f"  • Demo Done = 'no':  {len(demo_updates) - yes_count:,}")

cr.execute("""
    CREATE TEMP TABLE tmp_lead_demo_sync (
        lid VARCHAR(255) PRIMARY KEY,
        ddone VARCHAR(20),
        dtype VARCHAR(50)
    ) ON COMMIT DROP;
""")

psycopg2.extras.execute_values(
    cr,
    "INSERT INTO tmp_lead_demo_sync (lid, ddone, dtype) VALUES %s",
    demo_updates,
    page_size=2000
)

cr.execute("""
    UPDATE crm_lead cl
    SET 
        custom_demo_done = t.ddone,
        custom_demo_type = t.dtype
    FROM tmp_lead_demo_sync t
    WHERE cl.custom_naming_series = t.lid;
""")
updated_count = cr.rowcount
conn.commit()

print(f"✓ Successfully updated demo fields across {updated_count:,} Leads!")

# 3. Clean default_code on product variants so they show clean product names
cr.execute("""
    UPDATE product_product
    SET default_code = NULL
    WHERE default_code ~ '^[0-9]+$';
""")
print(f"✓ Cleaned numeric code prefix from {cr.rowcount} product variants!")
conn.commit()

# 4. Check BYD Steel Structures
cr.execute("""
    SELECT id, name, custom_naming_series, custom_demo_done, custom_demo_type, product_id
    FROM crm_lead
    WHERE custom_naming_series = 'Lead014995';
""")
rec = cr.fetchone()
print("\nLead014995 (BYD Steel Structures) Record:")
print(f"  ID: {rec[0]}")
print(f"  Name: {rec[1]}")
print(f"  Series: {rec[2]}")
print(f"  Demo Done: {repr(rec[3])}")
print(f"  Demo Type: {repr(rec[4])}")
print(f"  Product ID: {rec[5]}")

