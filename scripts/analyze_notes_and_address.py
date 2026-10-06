import csv

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
    
    # We also want to handle multi-line / child table rows if lead ID repeats or child rows exist
    return headers, reader[data_start:]

headers, rows = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')
print("Total data rows in file_b.csv:", len(rows))

# Let's inspect column indices
name_idx = None
addr_idx = None
detailed_idx = None
note_idx = None
added_on_idx = None
added_by_idx = None

# Find main table headers (before '~') and child table headers (after '~')
main_headers = []
child_headers = []
is_child = False
for idx, h in enumerate(headers):
    if h == '~':
        is_child = True
        continue
    if not is_child:
        main_headers.append((idx + 1, h))
        if h in ['name', 'ID']: name_idx = idx + 1
        if h in ['custom_full_address', 'Full Address']: addr_idx = idx + 1
        if h in ['custom_detailed_info', 'Detailed Info']: detailed_idx = idx + 1
    else:
        child_headers.append((idx + 1, h))
        if h in ['note', 'Note']: note_idx = idx + 1
        if h in ['added_on', 'Added On']: added_on_idx = idx + 1
        if h in ['added_by', 'Added By']: added_by_idx = idx + 1

print(f"Indices: name={name_idx}, addr={addr_idx}, detailed={detailed_idx}, note={note_idx}, added_on={added_on_idx}, added_by={added_by_idx}")

# Let's aggregate by Lead ID
leads_data = {}
current_lid = None

for row in rows:
    if not any(row): continue
    lid_val = row[name_idx].strip().strip('"') if name_idx is not None and len(row) > name_idx and row[name_idx] else None
    if lid_val:
        current_lid = lid_val
        if current_lid not in leads_data:
            leads_data[current_lid] = {
                'address': '',
                'detailed_info': '',
                'notes': []
            }
        if addr_idx is not None and len(row) > addr_idx and row[addr_idx]:
            leads_data[current_lid]['address'] = row[addr_idx].strip()
        if detailed_idx is not None and len(row) > detailed_idx and row[detailed_idx]:
            leads_data[current_lid]['detailed_info'] = row[detailed_idx].strip()
    
    # Check child note in this row
    if current_lid and note_idx is not None and len(row) > note_idx and row[note_idx]:
        note_txt = row[note_idx].strip()
        if note_txt:
            added_on = row[added_on_idx].strip() if added_on_idx is not None and len(row) > added_on_idx else ''
            added_by = row[added_by_idx].strip() if added_by_idx is not None and len(row) > added_by_idx else ''
            leads_data[current_lid]['notes'].append({
                'note': note_txt,
                'added_on': added_on,
                'added_by': added_by
            })

print(f"Total Unique Leads in dataset: {len(leads_data):,}")
with_address = sum(1 for d in leads_data.values() if d['address'])
with_detailed = sum(1 for d in leads_data.values() if d['detailed_info'])
with_notes = sum(1 for d in leads_data.values() if d['notes'])
with_any_note = sum(1 for d in leads_data.values() if d['detailed_info'] or d['notes'])

print(f"Leads with Full Address: {with_address:,}")
print(f"Leads with Detailed Info: {with_detailed:,}")
print(f"Leads with Child Notes: {with_notes:,}")
print(f"Leads with Detailed Info OR Child Notes: {with_any_note:,}")

# Sample 5 leads with notes & address
print("\n--- SAMPLE 5 LEADS ---")
count = 0
for lid, d in leads_data.items():
    if d['detailed_info'] or d['notes'] or d['address']:
        print(f"\nLead: {lid}")
        print(f"  Address: {d['address']}")
        print(f"  Detailed Info: {d['detailed_info'][:100] if d['detailed_info'] else 'None'}")
        print(f"  Notes count: {len(d['notes'])}")
        for n in d['notes'][:2]:
            print(f"    - [{n['added_on']} by {n['added_by']}] {n['note'][:80]}")
        count += 1
        if count >= 5: break

