import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()
cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='crm_lead' AND column_name LIKE '%demo%';")
print(cr.fetchall())
