import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_name='todo_task';")
print("todo_task columns:")
for c in cr.fetchall():
    print(c)

cr.execute("SELECT count(*), count(distinct legacy_id), count(distinct lead_id) FROM todo_task;")
print("todo_task stats:", cr.fetchone())

