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
print(f"--- MAIL_MESSAGE FOR LEAD {lead_id} ---")
cr.execute("""
    SELECT mm.id, mm.date, mm.author_id, rp.name as author_name, mm.subtype_id, mm.message_type, mm.body
    FROM mail_message mm
    LEFT JOIN res_partner rp ON mm.author_id = rp.id
    WHERE mm.model = 'crm.lead' AND mm.res_id = %s
    ORDER BY mm.id ASC;
""", (lead_id,))
messages = cr.fetchall()
print(f"Total mail_messages: {len(messages)}")
for m in messages:
    print(f"ID: {m[0]} | Date: {m[1]} | Author: {m[3]} (ID {m[2]}) | Body: {m[6][:120] if m[6] else None}")

print(f"\n--- MAIL_ACTIVITY FOR LEAD {lead_id} ---")
cr.execute("""
    SELECT ma.id, ma.date_deadline, ma.user_id, ru.login, ma.summary, ma.note
    FROM mail_activity ma
    LEFT JOIN res_users ru ON ma.user_id = ru.id
    WHERE ma.res_model = 'crm.lead' AND ma.res_id = %s;
""", (lead_id,))
activities = cr.fetchall()
print(f"Total planned mail_activity: {len(activities)}")
for a in activities:
    print(a)

print(f"\n--- TODO_TASK FOR LEAD {lead_id} ---")
cr.execute("""
    SELECT tt.id, tt.legacy_id, tt.date, tt.allocated_to, tt.status, tt.name, tt.description
    FROM todo_task tt
    WHERE tt.lead_id = %s;
""", (lead_id,))
todos = cr.fetchall()
print(f"Total todo_task: {len(todos)}")
for t in todos:
    print(t)

# Also check how many total mail_messages exist across all crm_lead in the DB
cr.execute("SELECT count(*) FROM mail_message WHERE model = 'crm.lead';")
print(f"\nTotal mail_message for all crm.lead in DB: {cr.fetchone()[0]:,}")

