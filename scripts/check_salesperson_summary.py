import subprocess

sql = """
-- Check breakdown of leads per salesperson
SELECT 
    u.id as user_id,
    p.name as salesperson_name,
    count(l.id) as total_leads,
    count(t.id) as total_todos
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
LEFT JOIN crm_lead l ON l.user_id = u.id
LEFT JOIN todo_task t ON t.lead_id = l.id
GROUP BY u.id, p.name
HAVING count(l.id) > 0
ORDER BY total_leads DESC;
"""

cmd = f"sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 \"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""

proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
print("OUT:\n", proc.stdout)
print("ERR:\n", proc.stderr)
