import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("""
    SELECT pp.id, pp.default_code, pt.name, pp.product_tmpl_id
    FROM product_product pp
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    WHERE pt.name::text LIKE '%ERPNext%' OR pp.default_code::text LIKE '%2683%';
""")
for r in cr.fetchall():
    print(r)

# Check all products referenced by crm_lead
cr.execute("""
    SELECT DISTINCT cl.product_id, pp.default_code, pt.name
    FROM crm_lead cl
    JOIN product_product pp ON cl.product_id = pp.id
    JOIN product_template pt ON pp.product_tmpl_id = pt.id
    LIMIT 10;
""")
print("\nSample lead products:")
for r in cr.fetchall():
    print(r)

