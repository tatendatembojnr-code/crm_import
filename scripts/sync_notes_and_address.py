import csv
import psycopg2
import psycopg2.extras
import html
import time

print("="*80)
print("=== SYNCING FULL ADDRESS & NOTES ACROSS ALL LEADS ===")
print("="*80)

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
addr_idx = None
city_idx = None
detailed_idx = None
note_idx = None
added_on_idx = None
added_by_idx = None

is_child = False
for idx, h in enumerate(headers):
    if h == '~':
        is_child = True
        continue
    if not is_child:
        if h in ['name', 'ID']: name_idx = idx + 1
        if h in ['custom_full_address', 'Full Address']: addr_idx = idx + 1
        if h in ['custom_city_town', 'City /Town']: city_idx = idx + 1
        if h in ['custom_detailed_info', 'Detailed Info']: detailed_idx = idx + 1
    else:
        if h in ['note', 'Note']: note_idx = idx + 1
        if h in ['added_on', 'Added On']: added_on_idx = idx + 1
        if h in ['added_by', 'Added By']: added_by_idx = idx + 1

leads_dict = {}
current_lid = None

for row in rows:
    if not any(row): continue
    lid_val = row[name_idx].strip().strip('"') if name_idx is not None and len(row) > name_idx and row[name_idx] else None
    if lid_val:
        current_lid = lid_val
        if current_lid not in leads_dict:
            leads_dict[current_lid] = {
                'address': '',
                'city': '',
                'detailed_info': '',
                'notes': []
            }
        if addr_idx is not None and len(row) > addr_idx and row[addr_idx]:
            leads_dict[current_lid]['address'] = row[addr_idx].strip().strip('"')
        if city_idx is not None and len(row) > city_idx and row[city_idx]:
            leads_dict[current_lid]['city'] = row[city_idx].strip().strip('"')
        if detailed_idx is not None and len(row) > detailed_idx and row[detailed_idx]:
            leads_dict[current_lid]['detailed_info'] = row[detailed_idx].strip()
    
    if current_lid and note_idx is not None and len(row) > note_idx and row[note_idx]:
        note_txt = row[note_idx].strip()
        if note_txt:
            added_on = row[added_on_idx].strip() if added_on_idx is not None and len(row) > added_on_idx else ''
            added_by = row[added_by_idx].strip() if added_by_idx is not None and len(row) > added_by_idx else ''
            leads_dict[current_lid]['notes'].append({
                'note': note_txt,
                'added_on': added_on,
                'added_by': added_by
            })

def build_description(detailed_info, child_notes):
    parts = []
    if detailed_info:
        if '<' in detailed_info and '>' in detailed_info:
            parts.append(detailed_info)
        else:
            escaped = html.escape(detailed_info).replace('\n', '<br/>')
            parts.append(f"<p>{escaped}</p>")
    
    for n in child_notes:
        note_text = n['note']
        if '<' in note_text and '>' in note_text:
            formatted_note = note_text
        else:
            formatted_note = html.escape(note_text).replace('\n', '<br/>')
        
        meta = []
        if n.get('added_by'): meta.append(f"By: {html.escape(n['added_by'])}")
        if n.get('added_on'): meta.append(f"On: {html.escape(n['added_on'])}")
        meta_str = f" <em>({', '.join(meta)})</em>" if meta else ""
        parts.append(f"<div class='lead_note_entry' style='margin-top: 8px;'><strong>Note{meta_str}:</strong><div>{formatted_note}</div></div>")
    
    return "".join(parts) if parts else None

lead_updates = []
for lid, data in leads_dict.items():
    desc = build_description(data['detailed_info'], data['notes'])
    addr = data['address'] if data['address'] else None
    city = data['city'] if data['city'] else None
    if desc is not None or addr is not None or city is not None:
        lead_updates.append((lid, addr, city, desc))

print(f"Total leads prepared for database update: {len(lead_updates):,}")

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("""
    CREATE TEMP TABLE tmp_lead_notes_addr (
        lid VARCHAR(255) PRIMARY KEY,
        addr VARCHAR(255),
        city VARCHAR(255),
        notes TEXT
    ) ON COMMIT DROP;
""")

psycopg2.extras.execute_values(
    cr,
    "INSERT INTO tmp_lead_notes_addr (lid, addr, city, notes) VALUES %s",
    lead_updates,
    page_size=2000
)

# Update crm_lead: update street if addr is provided, update city if city is provided, update description if notes is provided
cr.execute("""
    UPDATE crm_lead cl
    SET
        street = COALESCE(t.addr, cl.street),
        city = COALESCE(cl.city, t.city),
        description = COALESCE(t.notes, cl.description)
    FROM tmp_lead_notes_addr t
    WHERE cl.custom_naming_series = t.lid;
""")
updated_count = cr.rowcount
conn.commit()

print(f"✓ Successfully updated {updated_count:,} Leads in PostgreSQL database!")

# Verification query
cr.execute("""
    SELECT count(*) FROM crm_lead WHERE street IS NOT NULL AND street != '';
""")
db_street = cr.fetchone()[0]

cr.execute("""
    SELECT count(*) FROM crm_lead WHERE description IS NOT NULL AND description != '';
""")
db_notes = cr.fetchone()[0]

print(f"\n--- POST-SYNC VERIFICATION ---")
print(f"Leads with Street (Full Address) in DB: {db_street:,}")
print(f"Leads with Description (Notes) in DB:   {db_notes:,}")

# Check BYD Steel Structures
cr.execute("""
    SELECT id, name, custom_naming_series, street, city, description
    FROM crm_lead
    WHERE custom_naming_series = 'Lead014995';
""")
rec = cr.fetchone()
print(f"\nLead014995 (BYD Steel Structures) Record:")
print(f"  ID: {rec[0]}")
print(f"  Name: {rec[1]}")
print(f"  Series: {rec[2]}")
print(f"  Full Address (street): {repr(rec[3])}")
print(f"  City: {repr(rec[4])}")
print(f"  Notes (description): {repr(rec[5])}")

