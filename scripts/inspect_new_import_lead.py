import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

lead_id = 78626
print("--- TODO_TASK RECORDS FOR LEAD 78626 ---")
cr.execute("""
    SELECT id, legacy_id, status, allocated_to, date, name, description, create_date, legacy_create_date
    FROM todo_task
    WHERE lead_id = %s
    ORDER BY id ASC;
""", (lead_id,))
for r in cr.fetchall():
    print(r)

print("\n--- MAIL_ACTIVITY RECORDS FOR LEAD 78626 ---")
cr.execute("""
    SELECT ma.id, ma.date_deadline, ru.login, ma.summary, ma.note
    FROM mail_activity ma
    LEFT JOIN res_users ru ON ma.user_id = ru.id
    WHERE ma.res_model = 'crm.lead' AND ma.res_id = %s;
""", (lead_id,))
for r in cr.fetchall():
    print(r)

print("\n--- MAIL_MESSAGE (CHATTER) FOR LEAD 78626 ---")
cr.execute("""
    SELECT mm.id, mm.date, rp.name, mm.body
    FROM mail_message mm
    LEFT JOIN res_partner rp ON mm.author_id = rp.id
    WHERE mm.model = 'crm.lead' AND mm.res_id = %s
    ORDER BY mm.id ASC;
""", (lead_id,))
for r in cr.fetchall():
    print(r[0], r[1], r[2], repr(r[3][:80]))

