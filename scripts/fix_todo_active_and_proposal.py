import csv
import psycopg2
import psycopg2.extras
import html
import re

print("=" * 85)
print("=== FIX 1: SET active=True ON ALL OPEN TODOS IN mail_activity ===")
print("=== FIX 2: SYNC custom_proposal_status FROM file_b.csv ===")
print("=" * 85)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# ─────────────────────────────────────────────────────────────────────────────
# FIX 1: Set active=True on all mail_activity for crm.lead that have active=NULL
# (The import script forgot to set active=True on Open todos)
# ─────────────────────────────────────────────────────────────────────────────
print("\n[FIX 1] Checking mail_activity active status...")

cr.execute("""
    SELECT 
        count(*) FILTER (WHERE active IS NULL) as null_active,
        count(*) FILTER (WHERE active = True) as true_active,
        count(*) FILTER (WHERE active = False) as false_active
    FROM mail_activity WHERE res_model = 'crm.lead'
""")
r = cr.fetchone()
print(f"  Before: active=NULL: {r[0]:,} | active=True: {r[1]:,} | active=False: {r[2]:,}")

# All Open todos imported from Frappe/ERPNext were inserted with active=NULL
# because the INSERT statement didn't include the 'active' column.
# Fix: set active=True for all NULL ones (they are all Open/pending todos).
cr.execute("""
    UPDATE mail_activity
    SET active = True
    WHERE res_model = 'crm.lead'
    AND active IS NULL
""")
fixed_active = cr.rowcount
print(f"  ✓ Set active=True on {fixed_active:,} mail_activity records")

conn.commit()

cr.execute("""
    SELECT 
        count(*) FILTER (WHERE active IS NULL) as null_active,
        count(*) FILTER (WHERE active = True) as true_active,
        count(*) FILTER (WHERE active = False) as false_active
    FROM mail_activity WHERE res_model = 'crm.lead'
""")
r = cr.fetchone()
print(f"  After:  active=NULL: {r[0]:,} | active=True: {r[1]:,} | active=False: {r[2]:,}")

# Verify Prosper Lead016051 specifically
cr.execute("""
    SELECT ma.id, ma.summary, ma.date_deadline, ma.active
    FROM mail_activity ma
    JOIN crm_lead cl ON cl.id = ma.res_id
    WHERE cl.custom_naming_series = 'Lead016051'
    AND ma.res_model = 'crm.lead'
""")
print(f"\n  Lead016051 (Prosper) activities now: {cr.fetchall()}")

# ─────────────────────────────────────────────────────────────────────────────
# FIX 2: Sync custom_proposal_status from file_b.csv
# ─────────────────────────────────────────────────────────────────────────────
print("\n[FIX 2] Syncing custom_proposal_status from file_b.csv...")

def parse_frappe_template_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ""
        if first == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start = i + 5
            return headers, reader[data_start:]
    return [str(c).strip() for c in reader[0]], reader[1:]

headers, rows = parse_frappe_template_csv('/tmp/gdrive_verify_2/file_b.csv')

# Find column indices (non-child only, stop at '~')
name_idx = None
proposal_idx = None
quote_idx = None
is_child = False

for idx, h in enumerate(headers):
    if h == '~':
        break  # Stop at child table marker
    if h in ['name', 'ID'] and name_idx is None:
        name_idx = idx + 1
    if h == 'custom_proposal' and proposal_idx is None:
        proposal_idx = idx + 1
    if h in ['custom_quote', 'Quote'] and quote_idx is None:
        quote_idx = idx + 1

print(f"  Column indices: name={name_idx}, proposal={proposal_idx}, quote={quote_idx}")

# Valid proposal values mapping from Frappe → Odoo
# Odoo Selection: ('Not Yet', 'Not Yet'), ('Proposed', 'Proposed'), ('Accepted', 'Accepted'), ('Rejected', 'Rejected')
PROPOSAL_MAP = {
    'not yet': 'Not Yet',
    'not_yet': 'Not Yet',
    'proposed': 'Proposed',
    'accepted': 'Accepted',
    'rejected': 'Rejected',
    'yes': 'Accepted',
    'no': 'Not Yet',
    '': None,
}

QUOTE_MAP = {
    'not yet quote': 'Not Yet',
    'not_yet_quote': 'Not Yet',
    'quoted': 'Proposed',
    'quote sent': 'Proposed',
    'accepted': 'Accepted',
    'rejected': 'Rejected',
    '': None,
}

proposal_updates = []
current_lid = None

for row in rows:
    if not any(row):
        continue
    lid_val = row[name_idx].strip().strip('"') if name_idx is not None and len(row) > name_idx and row[name_idx] else None
    if lid_val and lid_val.startswith('Lead'):
        current_lid = lid_val
        raw_proposal = (row[proposal_idx].strip() if proposal_idx is not None and len(row) > proposal_idx and row[proposal_idx] else '').strip('"')
        raw_quote = (row[quote_idx].strip() if quote_idx is not None and len(row) > quote_idx and row[quote_idx] else '').strip('"')

        # Map proposal
        proposal_val = PROPOSAL_MAP.get(raw_proposal.lower(), None)
        # If no proposal but has quote info, use that to infer
        if not proposal_val and raw_quote:
            q_lower = raw_quote.lower()
            if 'not yet' in q_lower:
                proposal_val = 'Not Yet'
            elif 'accept' in q_lower:
                proposal_val = 'Accepted'
            elif 'reject' in q_lower:
                proposal_val = 'Rejected'
            elif 'quot' in q_lower:
                proposal_val = 'Proposed'

        if current_lid and proposal_val:
            proposal_updates.append((current_lid, proposal_val))

print(f"  Leads with proposal values to sync: {len(proposal_updates):,}")
# Count breakdown
from collections import Counter
counts = Counter(v for _, v in proposal_updates)
for k, v in sorted(counts.items()):
    print(f"    • {k}: {v:,}")

if proposal_updates:
    # Create temp table and bulk update
    cr.execute("""
        CREATE TEMP TABLE tmp_proposal_sync (
            lid VARCHAR(255) PRIMARY KEY,
            proposal VARCHAR(50)
        ) ON COMMIT DROP;
    """)
    psycopg2.extras.execute_values(
        cr,
        "INSERT INTO tmp_proposal_sync (lid, proposal) VALUES %s",
        proposal_updates,
        page_size=2000
    )
    cr.execute("""
        UPDATE crm_lead cl
        SET custom_proposal_status = t.proposal
        FROM tmp_proposal_sync t
        WHERE cl.custom_naming_series = t.lid
    """)
    updated_proposal = cr.rowcount
    conn.commit()
    print(f"  ✓ Updated proposal status on {updated_proposal:,} leads!")

    # Verify Prosper
    cr.execute("""
        SELECT name, custom_naming_series, custom_proposal_status
        FROM crm_lead WHERE custom_naming_series = 'Lead016051'
    """)
    print(f"\n  Lead016051 (Prosper) proposal: {cr.fetchone()}")

# ─────────────────────────────────────────────────────────────────────────────
# FINAL VERIFICATION
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "=" * 85)
print("=== FINAL VERIFICATION ===")
print("=" * 85)

cr.execute("SELECT count(*) FROM mail_activity WHERE res_model='crm.lead' AND active=True")
print(f"Active (Open) todos visible in Odoo: {cr.fetchone()[0]:,}")

cr.execute("SELECT count(*) FROM mail_activity WHERE res_model='crm.lead' AND active IS NULL")
print(f"Still-NULL active todos:             {cr.fetchone()[0]:,}")

cr.execute("SELECT count(*) FROM crm_lead WHERE custom_proposal_status IS NOT NULL AND custom_proposal_status != ''")
print(f"Leads with proposal status set:      {cr.fetchone()[0]:,}")

cr.execute("""
    SELECT DISTINCT custom_proposal_status, count(*) 
    FROM crm_lead 
    WHERE custom_proposal_status IS NOT NULL 
    GROUP BY custom_proposal_status
""")
print(f"Proposal status breakdown: {cr.fetchall()}")

# Check Lead016051 todos
cr.execute("""
    SELECT ma.id, ma.summary, ma.date_deadline, ma.active
    FROM mail_activity ma
    JOIN crm_lead cl ON cl.id = ma.res_id
    WHERE cl.custom_naming_series = 'Lead016051'
    AND ma.res_model = 'crm.lead'
    ORDER BY ma.date_deadline
""")
print(f"\nLead016051 final todos: {cr.fetchall()}")

conn.close()
print("\n✅ All fixes applied successfully!")
