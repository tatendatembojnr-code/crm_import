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
    SELECT count(*) FROM mail_message 
    WHERE model = 'crm.lead' AND body LIKE '%To-Do%done%';
""")
todo_done_msgs = cr.fetchone()[0]

cr.execute("""
    SELECT count(*) FROM mail_message 
    WHERE model = 'crm.lead' AND (body NOT LIKE '%To-Do%done%' OR body IS NULL);
""")
other_msgs = cr.fetchone()[0]

print(f"Total 'To-Do done' messages on crm.lead: {todo_done_msgs:,}")
print(f"Other messages on crm.lead:               {other_msgs:,}")

cr.execute("""
    SELECT mm.id, mm.res_id, mm.date, mm.author_id, mm.body
    FROM mail_message mm
    WHERE mm.model = 'crm.lead' AND (body NOT LIKE '%To-Do%done%' OR body IS NULL)
    LIMIT 5;
""")
print("\nSample other messages:")
for r in cr.fetchall():
    print(r[0], r[1], r[2], r[3], repr(r[4][:60]) if r[4] else None)

