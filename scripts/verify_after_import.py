import subprocess

sql = (
    "UPDATE crm_lead SET user_id = COALESCE(create_uid, 2) WHERE user_id IS NULL; "
    "SELECT count(*) as total_leads, count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson FROM crm_lead; "
    "SELECT count(*) as total_todos, count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead FROM todo_task;"
)

cmd = f"sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 \"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""

proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=25)
print("OUT:\n", proc.stdout)
print("ERR:\n", proc.stderr)
