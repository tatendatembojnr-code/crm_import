import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

print("--- TODO_TASK STATS ---")
cr.execute("SELECT status, count(*) FROM todo_task GROUP BY status;")
for r in cr.fetchall():
    print(f"Status '{r[0]}': {r[1]:,}")

print("\n--- MAIL_ACTIVITY STATS ---")
cr.execute("SELECT count(*) FROM mail_activity WHERE res_model = 'crm.lead';")
total_act = cr.fetchone()[0]
print(f"Total mail_activity on crm.lead: {total_act:,}")

# Check how many mail_activities correspond to Closed todo_tasks
cr.execute("""
    SELECT count(ma.id)
    FROM mail_activity ma
    JOIN todo_task tt ON tt.lead_id = ma.res_id AND (tt.name = ma.summary OR ma.note LIKE '%' || tt.legacy_id || '%')
    WHERE ma.res_model = 'crm.lead' AND tt.status = 'Closed';
""")
print(f"mail_activity matching Closed todo_task: {cr.fetchone()[0]:,}")

print("\n--- MAIL_MESSAGE STATS ---")
cr.execute("SELECT count(*) FROM mail_message WHERE model = 'crm.lead';")
total_mm = cr.fetchone()[0]
print(f"Total mail_message on crm.lead: {total_mm:,}")

