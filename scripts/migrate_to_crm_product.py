import psycopg2
import psycopg2.extras

print("=" * 80)
print("=== MIGRATING crm_lead.crm_product_id FROM custom_product TEXT FIELD ===")
print("=" * 80)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# ── Step 1: Add crm_product_id column if not exists ──────────────────────────
cr.execute("""
    SELECT column_name FROM information_schema.columns
    WHERE table_name = 'crm_lead' AND column_name = 'crm_product_id'
""")
if not cr.fetchone():
    cr.execute("""
        ALTER TABLE crm_lead
        ADD COLUMN crm_product_id INTEGER REFERENCES crm_product(id) ON DELETE SET NULL;
    """)
    print("✓ Added crm_product_id column to crm_lead")
    conn.commit()
else:
    print("  crm_product_id column already exists")

# ── Step 2: Ensure crm_product table exists and has all products ──────────────
cr.execute("SELECT count(*) FROM crm_product")
existing = cr.fetchone()[0]
print(f"\n  crm_product records currently in DB: {existing}")

# ── Step 3: Get all distinct custom_product values from crm_lead ──────────────
cr.execute("""
    SELECT DISTINCT TRIM(custom_product) as prod_name, count(*) as cnt
    FROM crm_lead
    WHERE custom_product IS NOT NULL AND TRIM(custom_product) != ''
    GROUP BY TRIM(custom_product)
    ORDER BY cnt DESC
""")
all_products = cr.fetchall()
print(f"\n  Distinct custom_product values in crm_lead: {len(all_products)}")
for p in all_products:
    print(f"    \"{p[0]}\" => {p[1]:,} leads")

# ── Step 4: Find or create each product in crm_product ───────────────────────
print(f"\n  Ensuring all products exist in crm_product table...")
name_to_id = {}

# First get existing
cr.execute("SELECT id, name FROM crm_product")
for row in cr.fetchall():
    name_to_id[row[1].lower()] = row[0]

new_count = 0
for prod_name, cnt in all_products:
    key = prod_name.lower()
    if key not in name_to_id:
        cr.execute(
            "INSERT INTO crm_product (name, sequence, active) VALUES (%s, 50, True) RETURNING id",
            (prod_name,)
        )
        new_id = cr.fetchone()[0]
        name_to_id[key] = new_id
        new_count += 1
        print(f"    ✓ Created crm_product: \"{prod_name}\" (id={new_id})")

if new_count:
    conn.commit()
    print(f"  ✓ Created {new_count} new crm_product records")
else:
    print("  All products already exist in crm_product table")

# ── Step 5: Bulk-update crm_lead.crm_product_id using temp table ─────────────
print(f"\n  Bulk-updating crm_product_id on all leads...")

update_pairs = [(pid, name) for name, pid in name_to_id.items()]

cr.execute("""
    CREATE TEMP TABLE tmp_crm_product_map (
        prod_id   INTEGER,
        prod_name VARCHAR(255)
    ) ON COMMIT DROP;
""")

psycopg2.extras.execute_values(
    cr,
    "INSERT INTO tmp_crm_product_map (prod_id, prod_name) VALUES %s",
    update_pairs,
    page_size=500
)

cr.execute("""
    UPDATE crm_lead cl
    SET crm_product_id = t.prod_id
    FROM tmp_crm_product_map t
    WHERE LOWER(TRIM(cl.custom_product)) = t.prod_name
    AND cl.custom_product IS NOT NULL
    AND TRIM(cl.custom_product) != ''
""")
updated = cr.rowcount
conn.commit()
print(f"  ✓ Updated crm_product_id on {updated:,} leads!")

# ── Step 6: Verification ─────────────────────────────────────────────────────
print("\n" + "=" * 80)
print("=== VERIFICATION ===")
print("=" * 80)

cr.execute("SELECT count(*) FROM crm_lead WHERE crm_product_id IS NOT NULL")
linked = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM crm_lead WHERE custom_product IS NOT NULL AND custom_product != '' AND crm_product_id IS NULL")
unlinked = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM crm_lead")
total = cr.fetchone()[0]

print(f"Total leads:                    {total:,}")
print(f"Leads with crm_product_id set:  {linked:,}")
print(f"Leads still missing (had data): {unlinked:,}  <-- should be 0")

print("\nTop products by lead count:")
cr.execute("""
    SELECT cp.name, count(cl.id) as cnt
    FROM crm_lead cl
    JOIN crm_product cp ON cp.id = cl.crm_product_id
    GROUP BY cp.name
    ORDER BY cnt DESC
""")
for r in cr.fetchall():
    print(f"  {r[0]}: {r[1]:,} leads")

conn.close()
print("\n✅ Migration complete!")
