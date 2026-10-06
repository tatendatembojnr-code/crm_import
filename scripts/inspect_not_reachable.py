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
    SELECT ma.id, ma.date_deadline, ma.summary, ma.note, ru.login
    FROM mail_activity ma
    LEFT JOIN res_users ru ON ma.user_id = ru.id
    WHERE ma.res_model = 'crm.lead' AND ma.res_id = 78626;
""")
print("Current mail_activity for 78626:")
for r in cr.fetchall():
    print(r)

