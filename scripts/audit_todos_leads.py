import subprocess

sql = """
-- 1. Check Leads
SELECT 
    count(*) as total_leads,
    count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson,
    count(CASE WHEN create_uid IS NULL THEN 1 END) as leads_without_creator
FROM crm_lead;

-- 2. Check To-Dos
SELECT 
    count(*) as total_todos,
    count(CASE WHEN lead_id IS NOT NULL THEN 1 END) as todos_linked_to_lead,
    count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead,
    count(CASE WHEN allocated_to IS NOT NULL THEN 1 END) as todos_with_allocated_to
FROM todo_task;

-- 3. Check sample unlinked todos if any
SELECT id, name, reference_type, reference_name, allocated_to 
FROM todo_task 
WHERE lead_id IS NULL 
LIMIT 10;

-- 4. Check breakdown of leads per salesperson
SELECT 
    u.id as salesperson_id,
    p.name as salesperson_name,
    count(l.id) as total_leads
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
JOIN crm_lead l ON l.user_id = u.id
GROUP BY u.id, p.name
ORDER BY total_leads DESC;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)
