import csv

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

headers, rows = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_a.csv')

# Search for Lead014995
lid_idx = None
status_idx = None
allocated_idx = None
desc_idx = None
date_idx = None
name_idx = None
modified_by_idx = None
owner_idx = None

for i, h in enumerate(headers):
    if h in ['reference_name', 'Reference Name']: lid_idx = i + 1
    if h in ['status', 'Status']: status_idx = i + 1
    if h in ['allocated_to', 'Allocated To']: allocated_idx = i + 1
    if h in ['description', 'Description']: desc_idx = i + 1
    if h in ['date', 'Date', 'due_date']: date_idx = i + 1
    if h in ['name', 'ID']: name_idx = i + 1
    if h in ['owner', 'Owner']: owner_idx = i + 1
    if h in ['modified_by', 'Modified By']: modified_by_idx = i + 1

print(f"Indices: lid={lid_idx}, status={status_idx}, alloc={allocated_idx}, desc={desc_idx}, date={date_idx}, name={name_idx}")

print("\n--- ALL TODOS FOR Lead014995 IN CSV ---")
for r in rows:
    if len(r) > lid_idx and r[lid_idx].strip().strip('"') == 'Lead014995':
        tid = r[name_idx].strip() if len(r) > name_idx else ''
        st = r[status_idx].strip() if len(r) > status_idx else ''
        alloc = r[allocated_idx].strip() if len(r) > allocated_idx else ''
        owner = r[owner_idx].strip() if len(r) > owner_idx else ''
        dt = r[date_idx].strip() if len(r) > date_idx else ''
        desc = r[desc_idx].strip() if len(r) > desc_idx else ''
        print(f"ID: {tid} | Status: {st} | Alloc: {alloc} | Owner: {owner} | Date: {dt} | Desc: {desc[:60]}")

