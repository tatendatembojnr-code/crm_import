import subprocess

sql = """
SELECT count(*) as total_leads FROM crm_lead;
SELECT count(*) as null_user_leads FROM crm_lead WHERE user_id IS NULL;
SELECT create_uid, count(*) FROM crm_lead WHERE user_id IS NULL GROUP BY create_uid;
SELECT u.id, u.login, p.name, count(l.id) as assigned_leads
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
LEFT JOIN crm_lead l ON l.user_id = u.id
GROUP BY u.id, u.login, p.name
ORDER BY assigned_leads DESC;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
