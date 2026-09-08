import os
import sys
import psycopg2

DB_NAME = os.getenv("ODOO_DB", "showline_s2_havano_pro_xcynznxmwcotukbxkm")
DB_USER = os.getenv("ODOO_DB_USER", "Showline")
DB_PASS = os.getenv("ODOO_DB_PASS", "Showline@#$1234")
DB_HOST = os.getenv("ODOO_DB_HOST", "192.168.112.2")
DB_PORT = os.getenv("ODOO_DB_PORT", "5432")

def fix_product_interests():
    print(f"Connecting to PostgreSQL '{DB_NAME}' at {DB_HOST}:{DB_PORT}...", flush=True)
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        print(f"Error connecting to database: {e}", file=sys.stderr)
        return

    conn.autocommit = True
    cur = conn.cursor()

    # Step 1: Find all distinct product names from custom_product and Opportunity names
    print("Finding distinct product interests on crm_lead...", flush=True)
    cur.execute("""
        SELECT DISTINCT COALESCE(NULLIF(TRIM(custom_product), ''), NULLIF(TRIM(SPLIT_PART(name, ' - ', 2)), '')) AS prod_name
        FROM crm_lead
        WHERE (product_id IS NULL)
          AND (
            (custom_product IS NOT NULL AND TRIM(custom_product) != '')
            OR (name LIKE '% - %')
          );
    """)
    distinct_prods = [r[0] for r in cur.fetchall() if r[0]]
    print(f"Found {len(distinct_prods)} distinct product values: {distinct_prods}", flush=True)

    # Step 2: For each product, find or create product_template and product_product in Postgres
    for prod_name in distinct_prods:
        clean_name = prod_name.strip()
        if not clean_name:
            continue

        # Check existing product_product
        cur.execute("""
            SELECT p.id
            FROM product_product p
            JOIN product_template t ON p.product_tmpl_id = t.id
            WHERE LOWER(t.name->>'en_US') = LOWER(%s)
               OR LOWER(t.name::text) LIKE %s
               OR LOWER(p.default_code) = LOWER(%s)
            LIMIT 1;
        """, (clean_name, f'%"{clean_name.lower()}"%', clean_name))
        row = cur.fetchone()

        if row:
            prod_id = row[0]
            print(f"Found existing product.product ID {prod_id} for '{clean_name}'", flush=True)
        else:
            # Create product_template and product_product directly
            cur.execute("""
                INSERT INTO product_template (name, type, detailed_type, categ_id, sale_ok, purchase_ok, active, create_date, write_date)
                VALUES (jsonb_build_object('en_US', %s), 'consu', 'consu', 1, true, false, true, NOW(), NOW())
                RETURNING id;
            """, (clean_name,))
            tmpl_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO product_product (product_tmpl_id, default_code, active, create_date, write_date)
                VALUES (%s, %s, true, NOW(), NOW())
                RETURNING id;
            """, (tmpl_id, clean_name))
            prod_id = cur.fetchone()[0]
            print(f"Created new product.product ID {prod_id} (tmpl {tmpl_id}) for '{clean_name}'", flush=True)

        # Step 3: Update crm_lead records
        cur.execute("""
            UPDATE crm_lead
            SET product_id = %s,
                custom_product = COALESCE(NULLIF(custom_product, ''), %s)
            WHERE product_id IS NULL
              AND (
                LOWER(TRIM(custom_product)) = LOWER(%s)
                OR ( (custom_product IS NULL OR TRIM(custom_product) = '') AND LOWER(TRIM(SPLIT_PART(name, ' - ', 2))) = LOWER(%s) )
              );
        """, (prod_id, clean_name, clean_name, clean_name))
        print(f"Updated {cur.rowcount:,} leads with Product Interest = '{clean_name}'", flush=True)

    # Step 4: Summary count
    cur.execute("SELECT count(*) FROM crm_lead WHERE product_id IS NOT NULL;")
    total_with_product = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM crm_lead;")
    total_leads = cur.fetchone()[0]
    print(f"\nCompleted! {total_with_product:,} of {total_leads:,} leads now have Product Interest populated.", flush=True)

    cur.close()
    conn.close()

if __name__ == '__main__':
    fix_product_interests()
