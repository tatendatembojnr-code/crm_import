import csv

def parse_frappe_template_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    headers = [str(c).strip() if c is not None else "" for c in reader[0]]
    data_start = 1
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ""
        if first == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start = i + 5
            return headers, reader[data_start:], True
    return headers, reader[1:], False

headers, rows, is_template = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')
print(f"is_template: {is_template}")
for i, h in enumerate(headers):
    print(f"Index {i} (Col {i+1}): {repr(h)}")

# Find source and name indices
for r in rows[:5]:
    print("Row len:", len(r))
    print("  Col 1 (ID):", r[1])
    print("  Col 3 (source):", r[3])

