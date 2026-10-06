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
CREATE OR REPLACE VIEW crm_hourly_activity_log AS (
    WITH raw_events AS (
        -- Leads created
        SELECT 
            COALESCE(create_uid, user_id) AS user_id,
            create_date AS event_time
        FROM crm_lead
        WHERE COALESCE(create_uid, user_id) IS NOT NULL AND create_date IS NOT NULL
        
        UNION ALL
        
        -- Leads updated
        SELECT 
            write_uid AS user_id,
            write_date AS event_time
        FROM crm_lead
        WHERE write_uid IS NOT NULL AND write_date IS NOT NULL AND write_date != create_date
        
        UNION ALL
        
        -- Mail activities on CRM leads
        SELECT 
            COALESCE(user_id, create_uid) AS user_id,
            create_date AS event_time
        FROM mail_activity
        WHERE res_model = 'crm.lead' AND create_date IS NOT NULL
        
        UNION ALL
        
        -- Chatter messages / calls / notes logged on CRM leads
        SELECT 
            (SELECT ru.id FROM res_users ru WHERE ru.partner_id = m.author_id LIMIT 1) AS user_id,
            m.create_date AS event_time
        FROM mail_message m
        WHERE m.model = 'crm.lead' AND m.create_date IS NOT NULL AND m.author_id IS NOT NULL
        
        UNION ALL
        
        -- To-Dos created / assigned
        SELECT 
            create_uid AS user_id,
            create_date AS event_time
        FROM todo_task
        WHERE create_date IS NOT NULL AND create_uid IS NOT NULL
    ),
    events_with_hour AS (
        SELECT 
            e.user_id,
            (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
            EXTRACT(HOUR FROM (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg'))::int AS hour_val
        FROM raw_events e
        WHERE e.user_id IS NOT NULL
    )
    SELECT 
        ROW_NUMBER() OVER (ORDER BY eh.activity_date DESC, COUNT(*) DESC, eh.user_id ASC) AS id,
        eh.user_id AS user_id,
        eh.activity_date AS activity_date,
        COUNT(CASE WHEN eh.hour_val = 7 THEN 1 END) AS h07_08,
        COUNT(CASE WHEN eh.hour_val = 8 THEN 1 END) AS h08_09,
        COUNT(CASE WHEN eh.hour_val = 9 THEN 1 END) AS h09_10,
        COUNT(CASE WHEN eh.hour_val = 10 THEN 1 END) AS h10_11,
        COUNT(CASE WHEN eh.hour_val = 11 THEN 1 END) AS h11_12,
        COUNT(CASE WHEN eh.hour_val = 12 THEN 1 END) AS h12_01,
        COUNT(CASE WHEN eh.hour_val = 13 THEN 1 END) AS h01_02,
        COUNT(CASE WHEN eh.hour_val = 14 THEN 1 END) AS h02_03,
        COUNT(CASE WHEN eh.hour_val = 15 THEN 1 END) AS h03_04,
        COUNT(CASE WHEN eh.hour_val = 16 THEN 1 END) AS h04_05,
        COUNT(CASE WHEN eh.hour_val = 17 THEN 1 END) AS h05_06,
        COUNT(*) AS total_count
    FROM events_with_hour eh
    JOIN res_users u ON u.id = eh.user_id
    WHERE u.active IS TRUE
    GROUP BY eh.user_id, eh.activity_date
);
""")
conn.commit()
print("✓ View created!")

cr.execute("""
    SELECT 
        p.name AS salesperson,
        v.activity_date,
        v.h07_08, v.h08_09, v.h09_10, v.h10_11, v.h11_12, v.h12_01,
        v.h01_02, v.h02_03, v.h03_04, v.h04_05, v.h05_06,
        v.total_count
    FROM crm_hourly_activity_log v
    JOIN res_users u ON u.id = v.user_id
    JOIN res_partner p ON p.id = u.partner_id
    WHERE v.activity_date = CURRENT_DATE
    ORDER BY v.total_count DESC, p.name ASC;
""")
rows = cr.fetchall()
print(f"\n✓ Found {len(rows)} salespersons active Today ({rows[0][1] if rows else 'N/A'}):")
print("-" * 125)
print(f"{'Salesperson':<25} | {'7-8':>4} | {'8-9':>4} | {'9-10':>4} | {'10-11':>5} | {'11-12':>5} | {'12-1':>4} | {'1-2':>4} | {'2-3':>4} | {'3-4':>4} | {'4-5':>4} | {'5-6':>4} | {'Total':>6}")
print("-" * 125)
for r in rows:
    print(f"{r[0]:<25} | {r[2]:>4} | {r[3]:>4} | {r[4]:>4} | {r[5]:>5} | {r[6]:>5} | {r[7]:>4} | {r[8]:>4} | {r[9]:>4} | {r[10]:>4} | {r[11]:>4} | {r[12]:>4} | {r[13]:>6}")
print("-" * 125)

conn.close()
