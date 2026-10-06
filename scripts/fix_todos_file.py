import subprocess

sql = """
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

SELECT count(*) as total_leads, count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson FROM crm_lead;
SELECT count(*) as total_todos, count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead FROM todo_task;
"""

# Write sql to remote /tmp/fix_todos.sql and run psql -f /tmp/fix_todos.sql
cmd_write = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"cat << 'EOF' > /tmp/fix_todos.sql\n{sql}\nEOF\""
)
subprocess.run(cmd_write, shell=True, check=True)

cmd_exec = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec -i psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm < /tmp/fix_todos.sql\""
)
res = subprocess.run(cmd_exec, shell=True, capture_output=True, text=True)
print("EXEC RESULT:\n", res.stdout)
print("STDERR:\n", res.stderr)
