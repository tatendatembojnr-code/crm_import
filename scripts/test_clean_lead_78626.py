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
print(f"--- BEFORE CLEANUP FOR LEAD {lead_id} ---")
cr.execute("SELECT count(*) FROM mail_activity WHERE res_model='crm.lead' AND res_id=%s;", (lead_id,))
print(f"mail_activity count: {cr.fetchone()[0]}")
cr.execute("SELECT count(*) FROM mail_message WHERE model='crm.lead' AND res_id=%s;", (lead_id,))
print(f"mail_message count: {cr.fetchone()[0]}")

# 1. Inspect todos for this lead
cr.execute("""
    SELECT id, legacy_id, status, allocated_to, date, name, description
    FROM todo_task
    WHERE lead_id = %s
    ORDER BY id ASC;
""", (lead_id,))
todos = cr.fetchall()
print("\ntodo_task records:")
for t in todos:
    print(t)

