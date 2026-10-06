import subprocess

sql = """
-- Inspect exactly what the 18 rows are
SELECT id, name, reference_type, reference_name, allocated_to FROM todo_task WHERE lead_id IS NULL;

-- Create 18 distinct leads and link each todo by id directly
DO $$
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
END $$;

SELECT count(*) as todos_without_lead FROM todo_task WHERE lead_id IS NULL;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
