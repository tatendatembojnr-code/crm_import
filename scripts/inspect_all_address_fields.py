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

# Find all columns related to address, street, location, notes
for i, h in enumerate(headers):
    hl = h.lower()
    if any(k in hl for k in ['address', 'street', 'city', 'town', 'state', 'country', 'territory', 'location', 'note', 'info', 'detail', 'desc']):
        count_non_empty = sum(1 for r in rows if len(r) > i + 1 and r[i + 1].strip())
        print(f"Col {i+1}: '{h}' -> Non-empty count: {count_non_empty:,}")

