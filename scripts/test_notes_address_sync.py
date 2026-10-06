import csv
import psycopg2
import psycopg2.extras
import html

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
        # If it doesn't contain HTML tags, wrap/format with <p>
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

# Prepare updates
lead_updates = []
for lid, data in leads_dict.items():
    desc = build_description(data['detailed_info'], data['notes'])
    addr = data['address'] if data['address'] else None
    city = data['city'] if data['city'] else None
    if desc or addr or city:
        lead_updates.append((lid, addr, city, desc))

print(f"Total leads to update: {len(lead_updates):,}")
print("Sample updates (first 3):")
for u in lead_updates[:3]:
    print(f"LID: {u[0]}, Addr: {u[1]}, City: {u[2]}, Desc Preview: {u[3][:80] if u[3] else None}")

# Check BYD Steel Structures
byd = next((u for u in lead_updates if u[0] == 'Lead014995'), None)
print("\nBYD Steel Structures update:", byd)

