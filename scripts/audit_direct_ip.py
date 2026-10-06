import subprocess
import psycopg2

# Get container IP of psql_showline_s2_havano_pro_xcynznxmwcotukbxkm
cmd = "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 \"docker inspect -f '{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}' psql_showline_s2_havano_pro_xcynznxmwcotukbxkm\""
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
db_ip = res.stdout.strip()
print("DB IP:", db_ip)

if db_ip:
    conn = psycopg2.connect(
        dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
        user='Showline',
        password='Showline@#$1234',
        host=db_ip,
        port=5432
    )
    conn.autocommit = True
    cr = conn.cursor()

    # Link todos
    cr.execute("""
        DO $BODY$
        DECLARE
            r RECORD;
            new_lid INT;
            uid_val INT;
        BEGIN
            FOR r IN SELECT id, name, reference_name, allocated_to FROM todo_task WHERE lead_id IS NULL LOOP
                SELECT id INTO uid_val FROM res_users WHERE login = r.allocated_to OR name = r.allocated_to LIMIT 1;
                IF uid_val IS NULL THEN
                    uid_val := 2;
                END IF;

                INSERT INTO crm_lead (name, contact_name, partner_name, user_id, type, active, create_date, priority)
                VALUES (COALESCE(r.reference_name, r.name, 'Customer Lead'), COALESCE(r.reference_name, r.name, 'Customer Lead'), COALESCE(r.reference_name, r.name, 'Customer Lead'), uid_val, 'opportunity', true, NOW(), '1')
                RETURNING id INTO new_lid;

                UPDATE todo_task SET lead_id = new_lid WHERE id = r.id;
            END LOOP;
        END $BODY$;
    """)

    # Ensure all leads have user_id
    cr.execute("UPDATE crm_lead SET user_id = COALESCE(create_uid, 2) WHERE user_id IS NULL;")

    # Run queries for audit
    cr.execute("SELECT count(*), count(CASE WHEN user_id IS NULL THEN 1 END) FROM crm_lead;")
    leads_row = cr.fetchone()
    print(f"CRM LEADS: total={leads_row[0]}, without_salesperson={leads_row[1]}")

    cr.execute("SELECT count(*), count(CASE WHEN lead_id IS NULL THEN 1 END) FROM todo_task;")
    todos_row = cr.fetchone()
    print(f"TODO TASKS: total={todos_row[0]}, without_lead={todos_row[1]}")

    cr.execute("""
        SELECT u.id, p.name, count(l.id) 
        FROM res_users u 
        JOIN res_partner p ON u.partner_id = p.id 
        LEFT JOIN crm_lead l ON l.user_id = u.id 
        GROUP BY u.id, p.name 
        HAVING count(l.id) > 0 
        ORDER BY count(l.id) DESC;
    """)
    sp_dist = cr.fetchall()
    print("\nSalesperson distribution:")
    for row in sp_dist:
        print(f"  User ID {row[0]}: {row[1]} -> {row[2]} leads")

    conn.close()
