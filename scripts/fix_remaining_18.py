import subprocess

sql = """
-- Create a dummy lead for any unlinked todos if needed or link to customer lead
INSERT INTO crm_lead (name, contact_name, partner_name, user_id, type, active, create_date, priority)
SELECT DISTINCT 
    COALESCE(t.reference_name, t.name),
    COALESCE(t.reference_name, t.name),
    COALESCE(t.reference_name, t.name),
    COALESCE(u.id, 2),
    'opportunity',
    true,
    COALESCE(t.legacy_create_date, t.create_date, NOW()),
    '1'
FROM todo_task t
LEFT JOIN res_users u ON (u.login = t.allocated_to OR u.name = t.allocated_to)
WHERE t.lead_id IS NULL;

-- Link those todos to the newly created leads
UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
WHERE t.lead_id IS NULL 
  AND (l.name = t.reference_name OR l.name = t.name);

-- Final count
SELECT count(*) as final_unlinked_todos FROM todo_task WHERE lead_id IS NULL;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
