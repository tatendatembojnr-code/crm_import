import csv
import psycopg2
import psycopg2.extras

print("="*80)
print("=== CREATING & SYNCHRONIZING LEAD SOURCES ACROSS ALL LEADS ===")
print("="*80)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# 1. Fetch current utm_source
cr.execute("SELECT lower(name), id, name FROM utm_source;")
utm_map = {r[0]: (r[1], r[2]) for r in cr.fetchall() if r[0]}

# 2. Parse all unique sources from file_b.csv
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
source_idx = None
for idx, h in enumerate(headers):
    if h == '~':
        break
    if h in ['name', 'ID'] and name_idx is None: name_idx = idx + 1
    if h in ['source', 'Source'] and source_idx is None: source_idx = idx + 1

print(f"Indices: name={name_idx}, source={source_idx}")

sources_to_create = set()
lead_sources_data = []

# List of known sources from Lead Source.csv as well
known_sources = [
    "Advertisement", "Campaign", "Cold Calling", "Cold Visit",
    "Customer's Vendor", "Exhibition", "Existing Customer", "FACEBOOK",
    "Facebook July Ad", "lead", "LEADS", "Mass Mailing", "other",
    "Reference", "Supplier Reference", "Walk In", "whatsapp"
]
for ks in known_sources:
    if ks.strip().lower() not in utm_map:
        sources_to_create.add(ks.strip())

for r in rows:
    if not any(r): continue
    lid = r[name_idx].strip().strip('"') if name_idx is not None and len(r) > name_idx else None
    src = r[source_idx].strip().strip('"') if source_idx is not None and len(r) > source_idx and r[source_idx] else None
    if src:
        if src.lower() not in utm_map:
            sources_to_create.add(src)
        if lid:
            lead_sources_data.append((lid, src))

if sources_to_create:
    print(f"New Sources to insert into utm_source: {len(sources_to_create)}")
    for s in sorted(sources_to_create):
        print(f"  • Creating source: '{s}'")
        cr.execute("""
            INSERT INTO utm_source (name, create_uid, write_uid, create_date, write_date)
            VALUES (%s, 1, 1, NOW(), NOW())
            RETURNING id, name;
        """, (s,))
        new_id, new_name = cr.fetchone()
        utm_map[s.lower()] = (new_id, new_name)

# 3. Prepare lead source updates
lead_updates = []
for lid, src in lead_sources_data:
    src_info = utm_map.get(src.lower())
    if src_info:
        source_id = src_info[0]
        source_name = src_info[1]
        lead_updates.append((lid, source_id, source_name))

print(f"\nUpdating source_id for {len(lead_updates):,} leads in database...")

cr.execute("""
    CREATE TEMP TABLE tmp_lead_source_sync (
        lid VARCHAR(255) PRIMARY KEY,
        sid INT,
        sname VARCHAR(255)
    ) ON COMMIT DROP;
""")

psycopg2.extras.execute_values(
    cr,
    "INSERT INTO tmp_lead_source_sync (lid, sid, sname) VALUES %s",
    lead_updates,
    page_size=2000
)

cr.execute("""
    UPDATE crm_lead cl
    SET 
        source_id = t.sid,
        custom_lead_source = t.sname
    FROM tmp_lead_source_sync t
    WHERE cl.custom_naming_series = t.lid;
""")
updated = cr.rowcount
conn.commit()

print(f"✓ Successfully updated {updated:,} Leads with their Lead Source!")

# 4. Verification
cr.execute("""
    SELECT count(*) FROM crm_lead WHERE source_id IS NOT NULL;
""")
leads_with_src = cr.fetchone()[0]
print(f"\n--- POST-SYNC VERIFICATION ---")
print(f"Total Leads with Source in DB: {leads_with_src:,}")

cr.execute("""
    SELECT cl.id, cl.name, cl.custom_naming_series, cl.source_id, us.name, cl.custom_lead_source
    FROM crm_lead cl
    LEFT JOIN utm_source us ON cl.source_id = us.id
    WHERE cl.custom_naming_series = 'Lead014995';
""")
rec = cr.fetchone()
print("\nLead014995 (BYD Steel Structures) Source status:")
print(f"  ID: {rec[0]}")
print(f"  Name: {rec[1]}")
print(f"  Series: {rec[2]}")
print(f"  Source ID: {rec[3]}")
print(f"  Source Name: {repr(rec[4])}")
print(f"  Custom Source: {repr(rec[5])}")

