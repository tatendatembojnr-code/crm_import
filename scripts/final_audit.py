import subprocess

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c "
    "'SELECT count(*) as total_leads, count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson, count(CASE WHEN create_uid IS NULL THEN 1 END) as leads_without_user FROM crm_lead; "
    "SELECT count(*) as total_todos, count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead FROM todo_task;'\""
)
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("FINAL AUDIT RESULTS:\n", res.stdout)
