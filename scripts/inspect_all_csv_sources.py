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

headers, rows = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')

source_idx = None
name_idx = None
for i, h in enumerate(headers):
    if h in ['source', 'Source']: source_idx = i + 1
    if h in ['name', 'ID']: name_idx = i + 1

sources_count = {}
lead_sources = []
for r in rows:
    if not any(r): continue
    lid = r[name_idx].strip().strip('"') if name_idx is not None and len(r) > name_idx else None
    src = r[source_idx].strip().strip('"') if source_idx is not None and len(r) > source_idx and r[source_idx] else None
    if src:
        sources_count[src] = sources_count.get(src, 0) + 1
        if lid:
            lead_sources.append((lid, src))

print(f"Total leads with source: {len(lead_sources):,}")
print("Unique sources across all leads:")
for s, c in sorted(sources_count.items(), key=lambda x: -x[1]):
    print(f"  • '{s}': {c:,} leads")

