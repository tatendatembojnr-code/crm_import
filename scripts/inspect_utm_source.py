import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("SELECT id, name FROM utm_source;")
print("Existing utm_source in DB:")
for r in cr.fetchall():
    print(r)

cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='crm_lead' AND column_name LIKE '%source%';")
print("\nSource columns on crm_lead:")
for r in cr.fetchall():
    print(r)

cr.execute("SELECT id, name, source_id, custom_lead_source FROM crm_lead WHERE id = 78626;")
print("\nLead 78626 sources:", cr.fetchone())

