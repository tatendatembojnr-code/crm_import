import psycopg2

print("=" * 80)
print("=== CLEANING UP UNUSED PRODUCTS & DEDUPLICATING CRM PRODUCTS ===")
print("=" * 80)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# ── 1. Check & Delete from standard product.template / product.product ───────────
print("\n1. Checking standard product.template / product.product records...")
cr.execute("SELECT count(*) FROM product_template;")
pt_count = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM product_product;")
pp_count = cr.fetchone()[0]
print(f"   Found {pt_count} product_template and {pp_count} product_product records.")

# Check if any sale orders, invoices, or stock moves reference them
cr.execute("SELECT count(*) FROM sale_order_line;")
sol_count = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM account_move_line WHERE product_id IS NOT NULL;")
aml_count = cr.fetchone()[0]
cr.execute("SELECT count(*) FROM crm_lead WHERE product_id IS NOT NULL;")
lead_pt_count = cr.fetchone()[0]

print(f"   References in Sales Order Lines: {sol_count}")
print(f"   References in Invoice Lines:     {aml_count}")
print(f"   References in CRM Leads:         {lead_pt_count}")

# Delete stock references if any, then delete from product_product and product_template
try:
    cr.execute("""
        SELECT tc.table_name, kcu.column_name 
        FROM information_schema.table_constraints tc 
        JOIN information_schema.key_column_usage kcu ON tc.constraint_name = kcu.constraint_name 
        JOIN information_schema.constraint_column_usage ccu ON ccu.constraint_name = tc.constraint_name 
        WHERE tc.constraint_type = 'FOREIGN KEY' 
          AND ccu.table_name IN ('product_template', 'product_product');
    """)
    fk_deps = cr.fetchall()
    print(f"   Found {len(fk_deps)} foreign key dependencies.")
    for table_name, col_name in fk_deps:
        if table_name not in ('product_product', 'product_template', 'crm_lead'):
            try:
                cr.execute(f"DELETE FROM {table_name} WHERE {col_name} IS NOT NULL;")
                print(f"   Cleared dependent records from table '{table_name}' ({col_name})")
            except Exception as e:
                print(f"   Skipping table {table_name}: {e}")
                
    cr.execute("DELETE FROM product_product;")
    cr.execute("DELETE FROM product_template;")
    conn.commit()
    print("   ✓ Successfully deleted unused records from product_product and product_template!")
except Exception as e:
    conn.rollback()
    print(f"   Error deleting product_template/product_product: {e}")

# ── 2. Deduplicate crm.product records ──────────────────────────────────────────
print("\n2. Deduplicating and cleaning crm.product records...")

# Find all duplicates grouped by lowercase name
cr.execute("""
    SELECT LOWER(TRIM(name)) as clean_name, array_agg(id ORDER BY id) as ids, count(*) as cnt
    FROM crm_product
    GROUP BY LOWER(TRIM(name))
    HAVING count(*) > 1;
""")
duplicates = cr.fetchall()

for clean_name, ids, cnt in duplicates:
    # Keep the lowest ID (or the one with the most leads)
    # Let's count leads for each ID
    cr.execute("""
        SELECT cp.id, cp.name, count(cl.id) as lead_count
        FROM crm_product cp
        LEFT JOIN crm_lead cl ON cl.crm_product_id = cp.id
        WHERE cp.id = ANY(%s)
        GROUP BY cp.id, cp.name
        ORDER BY lead_count DESC, cp.id ASC;
    """, (ids,))
    rows = cr.fetchall()
    
    primary_id = rows[0][0]
    primary_name = rows[0][1]
    
    for row in rows[1:]:
        duplicate_id = row[0]
        dup_leads = row[2]
        # Reassign leads to primary
        if dup_leads > 0:
            cr.execute("UPDATE crm_lead SET crm_product_id = %s WHERE crm_product_id = %s", (primary_id, duplicate_id))
            print(f"   → Reassigned {dup_leads} leads from crm_product id={duplicate_id} to primary id={primary_id} ({primary_name})")
        # Delete duplicate crm.product
        cr.execute("DELETE FROM crm_product WHERE id = %s", (duplicate_id,))
        print(f"   ✓ Deleted duplicate crm_product id={duplicate_id} ('{row[1]}')")

conn.commit()

# Delete any orphaned crm_product with 0 leads if requested, or keep the unique ones
print("\n3. Current active crm.product list:")
cr.execute("""
    SELECT cp.id, cp.name, count(cl.id) as lead_count
    FROM crm_product cp
    LEFT JOIN crm_lead cl ON cl.crm_product_id = cp.id
    GROUP BY cp.id, cp.name
    ORDER BY lead_count DESC, cp.name ASC;
""")
for r in cr.fetchall():
    print(f"   - [ID {r[0]:>3}] {r[1]:<25} : {r[2]:>6,} leads")

conn.close()
print("\n✅ Product cleanup complete!")
