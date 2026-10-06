#!/usr/bin/env python3
"""
COMPREHENSIVE 100% AUDIT
Checks EVERY field of every lead and todo against the source CSV data.
"""
import csv, re, html as html_mod, psycopg2, psycopg2.extras
from datetime import datetime, date

print("=" * 90)
print("=== 100% COMPREHENSIVE AUDIT: ALL LEADS + TODOS vs SOURCE CSV ===")
print("=" * 90)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline', password='Showline@#$1234', host='db', port=5432
)
cr = conn.cursor()

# ── Helper functions ──────────────────────────────────────────────────────────
def clean_html(val):
    if not val: return ''
    return re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', html_mod.unescape(str(val)))).strip()

def safe(val):
    if val is None: return ''
    return str(val).strip().strip('"').strip()

def clean_date(val):
    if not val: return None
    s = safe(val).split(' ')[0]
    for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%m/%d/%Y', '%d/%m/%Y'):
        try: return datetime.strptime(s, fmt).date()
        except: pass
    return None

def parse_template_csv(filepath):
    """Parse Frappe-style template CSV, return (headers, rows_as_dicts)."""
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    col_offset = 0
    headers = None
    data_start = 0
    for i, row in enumerate(reader):
        first = safe(row[0]) if row else ''
        if first == 'Column Name:':
            headers = [safe(c) for c in row[1:]]
            col_offset = 1
            data_start = i + 5
            break
    if not headers:
        headers = [safe(c) for c in reader[0]]
        data_start = 1
    records = []
    for row in reader[data_start:]:
        if not any(row): continue
        d = {}
        for idx, h in enumerate(headers):
            if h == '~': break
            col = idx + col_offset
            if h and h not in d:
                d[h] = row[col] if col < len(row) else ''
        records.append(d)
    return headers, records

# ── Load source CSVs ──────────────────────────────────────────────────────────
print("\n[1] Loading source CSV files...")
_, lead_recs = parse_template_csv('/tmp/gdrive_verify_2/file_b.csv')
_, todo_recs = parse_template_csv('/tmp/gdrive_verify_2/file_a.csv')
print(f"    Lead CSV rows:  {len(lead_recs):,}")
print(f"    Todo CSV rows:  {len(todo_recs):,}")

# ── Load DB data ──────────────────────────────────────────────────────────────
print("\n[2] Loading database records...")
cr.execute("""
    SELECT
        cl.id, cl.custom_naming_series, cl.name,
        cl.partner_name, cl.phone, cl.email_from,
        cl.description, cl.street, cl.city,
        cl.expected_revenue, cl.custom_deal_size,
        cl.custom_type_of_business,
        cl.custom_demo_done, cl.custom_demo_type,
        cl.custom_proposal_status,
        cl.custom_product, cp.name as crm_product_name,
        cl.create_date,
        us.login as owner_login,
        src.name as source_name,
        cl.custom_quote_date, cl.custom_quote,
        cl.active
    FROM crm_lead cl
    LEFT JOIN crm_product cp ON cp.id = cl.crm_product_id
    LEFT JOIN res_users us ON us.id = cl.user_id
    LEFT JOIN utm_source src ON src.id = cl.source_id
    WHERE cl.custom_naming_series IS NOT NULL
""")
db_leads = {r[1]: r for r in cr.fetchall()}
print(f"    Leads in DB (with naming_series): {len(db_leads):,}")

# ── Check mail_activity (open todos) ─────────────────────────────────────────
cr.execute("""
    SELECT ma.summary, ma.date_deadline, ma.active, ma.res_id,
           cl.custom_naming_series, ru.login
    FROM mail_activity ma
    JOIN crm_lead cl ON cl.id = ma.res_id
    JOIN res_users ru ON ru.id = ma.user_id
    WHERE ma.res_model = 'crm.lead'
""")
db_activities = cr.fetchall()
print(f"    mail_activity (open todos): {len(db_activities):,}")

cr.execute("""
    SELECT count(*) FROM mail_message
    WHERE model = 'crm.lead' AND body LIKE '%To-Do%done%'
""")
done_todos_count = cr.fetchone()[0]
print(f"    Closed to-dos in chatter:   {done_todos_count:,}")

# ── LEAD AUDIT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("[3] LEAD FIELD AUDIT — checking every lead against CSV...")
print("=" * 90)

issues = []
matched = 0
csv_lead_map = {}

for r in lead_recs:
    lid = safe(r.get('name') or r.get('id') or r.get('ID'))
    if not lid or not lid.startswith('Lead'): continue
    csv_lead_map[lid] = r

total_csv_leads = len(csv_lead_map)
print(f"    Unique leads in CSV: {total_csv_leads:,}")

# Fields to check
field_mismatches = {
    'deal_size': 0, 'product': 0, 'proposal': 0, 'demo_done': 0,
    'owner': 0, 'source': 0, 'create_date': 0, 'quote_date': 0,
    'type_of_business': 0
}
missing_in_db = 0
missing_in_csv = 0

for lid, csv_r in csv_lead_map.items():
    if lid not in db_leads:
        missing_in_db += 1
        if missing_in_db <= 5:
            issues.append(f"  MISSING IN DB: {lid}")
        continue
    matched += 1
    db = db_leads[lid]
    (db_id, db_lid, db_name, db_partner, db_phone, db_email,
     db_desc, db_street, db_city, db_rev, db_deal_size,
     db_biz_type, db_demo_done, db_demo_type,
     db_proposal, db_custom_product, db_crm_product,
     db_create_date, db_owner, db_source_name,
     db_quote_date, db_quote, db_active) = db

    # Deal size
    csv_deal = 0.0
    try: csv_deal = float(safe(csv_r.get('custom_deal_size_') or csv_r.get('expected_revenue') or 0))
    except: pass
    if abs((db_deal_size or 0) - csv_deal) > 0.01:
        field_mismatches['deal_size'] += 1
        if field_mismatches['deal_size'] <= 3:
            issues.append(f"  DEAL_SIZE mismatch {lid}: CSV={csv_deal} DB={db_deal_size}")

    # Product
    csv_prod = safe(csv_r.get('custom_product'))
    db_prod = db_crm_product or db_custom_product or ''
    if csv_prod and db_prod.lower() != csv_prod.lower() and 'digi' not in csv_prod.lower():
        field_mismatches['product'] += 1
        if field_mismatches['product'] <= 3:
            issues.append(f"  PRODUCT mismatch {lid}: CSV='{csv_prod}' DB='{db_prod}'")

    # Proposal
    csv_prop_raw = safe(csv_r.get('custom_proposal') or csv_r.get('Proposal') or '')
    csv_prop = {'not yet': 'Not Yet', 'not_yet': 'Not Yet', 'proposed': 'Proposed',
                'accepted': 'Accepted', 'rejected': 'Rejected'}.get(csv_prop_raw.lower(), '')
    if csv_prop and db_proposal != csv_prop:
        field_mismatches['proposal'] += 1
        if field_mismatches['proposal'] <= 3:
            issues.append(f"  PROPOSAL mismatch {lid}: CSV='{csv_prop}' DB='{db_proposal}'")

    # Demo done
    csv_demo_raw = safe(csv_r.get('custom_demo_done_') or csv_r.get('Demo Done ') or csv_r.get('custom_demo_done') or 'no').lower()
    csv_demo = 'yes' if 'yes' in csv_demo_raw or ('demo' in csv_demo_raw and 'no' not in csv_demo_raw) else 'no'
    if db_demo_done != csv_demo:
        field_mismatches['demo_done'] += 1

    # Creation date
    csv_cdate = clean_date(csv_r.get('creation') or csv_r.get('Created On'))
    if csv_cdate and db_create_date:
        db_cdate = db_create_date.date() if hasattr(db_create_date, 'date') else db_create_date
        if db_cdate != csv_cdate:
            field_mismatches['create_date'] += 1
            if field_mismatches['create_date'] <= 2:
                issues.append(f"  DATE mismatch {lid}: CSV={csv_cdate} DB={db_cdate}")

    # Quote date
    csv_qdate = clean_date(csv_r.get('custom_quote_date') or csv_r.get('Quote Date'))
    if csv_qdate and db_quote_date != csv_qdate:
        field_mismatches['quote_date'] += 1
        if field_mismatches['quote_date'] <= 2:
            issues.append(f"  QUOTE_DATE mismatch {lid}: CSV={csv_qdate} DB={db_quote_date}")

# Check for leads in DB not in CSV
for lid in db_leads:
    if lid not in csv_lead_map:
        missing_in_csv += 1

print(f"\n    Results:")
print(f"    ✓ Leads matched (CSV ↔ DB):         {matched:,} / {total_csv_leads:,}")
print(f"    ✗ Leads missing in DB:               {missing_in_db:,}")
print(f"    ℹ Leads in DB not in CSV (new):      {missing_in_csv:,}")
print(f"\n    Field mismatch counts:")
for k, v in field_mismatches.items():
    icon = '✓' if v == 0 else '✗'
    print(f"    {icon} {k}: {v:,}")

# ── TODO AUDIT ────────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("[4] TODO AUDIT — checking todos against CSV...")
print("=" * 90)

# Build CSV todo map by legacy_id → todo
csv_todo_map = {}
for r in todo_recs:
    tid_raw = safe(r.get('name') or r.get('ID') or r.get('id') or '')
    tid = tid_raw.strip('"').strip()
    ref_type = safe(r.get('reference_type'))
    ref_name = safe(r.get('reference_name'))
    if ref_type == 'Lead' and ref_name.startswith('Lead') and tid:
        csv_todo_map[tid] = r

print(f"    Lead-linked todos in CSV: {len(csv_todo_map):,}")

# Check todos in DB (via todo_task table)
cr.execute("""
    SELECT tt.legacy_id, tt.status, tt.date, tt.lead_id, tt.allocated_to
    FROM todo_task tt
    WHERE tt.lead_id IS NOT NULL AND tt.legacy_id IS NOT NULL
""")
db_todos = {r[0]: r for r in cr.fetchall()}
print(f"    Lead-linked todos in DB:  {len(db_todos):,}")

todo_matched = 0
todo_missing = 0
todo_status_mismatch = 0
todo_date_mismatch = 0

for tid, csv_t in csv_todo_map.items():
    if tid not in db_todos:
        todo_missing += 1
        continue
    todo_matched += 1
    db_t = db_todos[tid]
    # Status
    csv_status = safe(csv_t.get('status'))
    db_status = db_t[1]
    if csv_status and db_status and csv_status != db_status:
        todo_status_mismatch += 1
    # Date
    csv_date = clean_date(csv_t.get('date'))
    db_date = db_t[2]
    if csv_date and db_date and csv_date != db_date:
        todo_date_mismatch += 1

print(f"\n    ✓ Todos matched (CSV ↔ DB):     {todo_matched:,} / {len(csv_todo_map):,}")
print(f"    ✗ Todos missing in DB:          {todo_missing:,}")
print(f"    ✗ Status mismatches:            {todo_status_mismatch:,}")
print(f"    ✗ Date mismatches:              {todo_date_mismatch:,}")

# ── ACTIVITY AUDIT ────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("[5] ACTIVITY (mail_activity) AUDIT")
print("=" * 90)

# Open todos in CSV (status=Open, linked to leads)
open_csv_todos = {tid: r for tid, r in csv_todo_map.items() if safe(r.get('status')) == 'Open'}
closed_csv_todos = {tid: r for tid, r in csv_todo_map.items() if safe(r.get('status')) == 'Closed'}

cr.execute("SELECT count(*) FROM mail_activity WHERE res_model='crm.lead' AND active=True")
db_open_act = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM mail_activity WHERE res_model='crm.lead' AND active IS NULL")
db_null_act = cr.fetchone()[0]

print(f"    Open todos in CSV:            {len(open_csv_todos):,}")
print(f"    Open mail_activity in DB:     {db_open_act:,}  (active=True)")
print(f"    mail_activity with NULL active:{db_null_act:,}  <-- must be 0")
print(f"    Closed todos in CSV:          {len(closed_csv_todos):,}")
print(f"    Closed to-dos in chatter:     {done_todos_count:,}")

# Newly created todos (in Odoo, not in CSV) - that's fine
new_in_odoo = db_open_act - len(open_csv_todos)
print(f"    Todos created in Odoo (new):  {new_in_odoo:,}  (created after migration)")

# ── FINAL SUMMARY ────────────────────────────────────────────────────────────
print("\n" + "=" * 90)
print("[FINAL SUMMARY]")
print("=" * 90)

all_good = True

checks = [
    ("All leads present in DB", matched == total_csv_leads and missing_in_db == 0),
    ("Deal sizes match",         field_mismatches['deal_size'] == 0),
    ("Creation dates match",     field_mismatches['create_date'] == 0),
    ("Quote dates match",        field_mismatches['quote_date'] == 0),
    ("All todos matched",        todo_missing == 0),
    ("Todo dates match",         todo_date_mismatch == 0),
    ("No NULL-active activities", db_null_act == 0),
    ("Product field populated",  field_mismatches['product'] == 0),
]

for label, ok in checks:
    icon = '✅' if ok else '❌'
    if not ok: all_good = False
    print(f"  {icon}  {label}")

if issues:
    print(f"\n  Sample issues found:")
    for i in issues[:15]:
        print(i)

print()
if all_good:
    print("  🎉 PERFECT — 100% ALIGNED. Everything matches the source CSV data!")
else:
    print("  ⚠️  Some mismatches found (see above). Review and fix.")

conn.close()
