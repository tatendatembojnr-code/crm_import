import psycopg2

conn = psycopg2.connect(dbname="showline_s2_havano_pro_xcynznxmwcotukbxkm", user="Showline", password="Showline@#$1234", host="192.168.112.2", port="5432")
conn.autocommit = True
cur = conn.cursor()

print("Sequencing leads based on legacy_create_date...")
cur.execute("SELECT id FROM crm_lead ORDER BY COALESCE(legacy_create_date, create_date) ASC, id ASC;")
leads = cur.fetchall()

print(f"Found {len(leads)} leads. Applying numbers...")
counter = 1
for lead_id, in leads:
    cur.execute("UPDATE crm_lead SET custom_no = %s WHERE id = %s", (counter, lead_id))
    counter += 1

print("Sequencing complete!")
cur.close()
conn.close()
