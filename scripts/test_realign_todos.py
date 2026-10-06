import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# Check user mapping
cr.execute("""
    SELECT lower(login), u.id, u.partner_id
    FROM res_users u
    WHERE login IS NOT NULL;
""")
user_map = {r[0]: (r[1], r[2]) for r in cr.fetchall()}
print(f"Users mapped: {len(user_map)}")

# Check activity types
cr.execute("SELECT id, name FROM mail_activity_type;")
print("Activity types:", cr.fetchall())

# Check subtypes
cr.execute("SELECT id, name FROM mail_message_subtype WHERE res_model='crm.lead' OR res_model IS NULL;")
print("Subtypes:", cr.fetchall())

