import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("SELECT id, default_code, name FROM product_template WHERE id IN (SELECT product_tmpl_id FROM product_product WHERE id = 2683);")
print("Product 2683 template:", cr.fetchall())

cr.execute("SELECT id, default_code, (SELECT name->>'en_US' FROM product_template pt WHERE pt.id=pp.product_tmpl_id) FROM product_product pp WHERE id = 2683;")
print("Product 2683 variant:", cr.fetchall())

