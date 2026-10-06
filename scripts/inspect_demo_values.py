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

d1_idx = None
d2_idx = None
for idx, h in enumerate(headers):
    if h == '~': break
    if h == 'custom_demo_done_': d1_idx = idx + 1
    if h == 'custom_demo_done_online_or_onsite': d2_idx = idx + 1

d1_vals = {}
d2_vals = {}

for r in rows:
    if not any(r): continue
    v1 = r[d1_idx].strip() if d1_idx is not None and len(r) > d1_idx else ''
    v2 = r[d2_idx].strip() if d2_idx is not None and len(r) > d2_idx else ''
    d1_vals[v1] = d1_vals.get(v1, 0) + 1
    d2_vals[v2] = d2_vals.get(v2, 0) + 1

print("--- custom_demo_done_ values in CSV ---")
for k, v in sorted(d1_vals.items(), key=lambda x: -x[1]):
    print(f"  • {repr(k)}: {v:,}")

print("\n--- custom_demo_done_online_or_onsite values in CSV ---")
for k, v in sorted(d2_vals.items(), key=lambda x: -x[1]):
    print(f"  • {repr(k)}: {v:,}")

