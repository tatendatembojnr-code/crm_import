import subprocess

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -t -A -c "
    "'SELECT count(*) FROM crm_lead; "
    "SELECT count(*) FROM crm_lead WHERE user_id IS NULL; "
    "SELECT count(*) FROM todo_task; "
    "SELECT count(*) FROM todo_task WHERE lead_id IS NULL;'\""
)
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("COUNTS:\n", res.stdout)
