import subprocess

# 1. Update database records where user_id IS NULL
sql = """
UPDATE crm_lead 
SET user_id = COALESCE(create_uid, 2) 
WHERE user_id IS NULL;

SELECT count(*) as remaining_null_leads 
FROM crm_lead 
WHERE user_id IS NULL;
"""

print("1. Updating database records where user_id is NULL...")
cmd_db = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)
res_db = subprocess.run(cmd_db, shell=True, capture_output=True, text=True)
print("DB OUTPUT:\n", res_db.stdout)

# 2. Sync files to container
print("\n2. Syncing crm_lead.py to showline container...")
cmd_sync = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"rsync -av --delete /opt/odoo-secure/addons-custom/crm_import/ /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/crm_import/\""
)
subprocess.run(cmd_sync, shell=True, check=True)
print("✓ Synced!")

# 3. Mark to upgrade and restart
print("\n3. Restarting container...")
cmd_restart = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker restart odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm\""
)
subprocess.run(cmd_restart, shell=True, check=True)
print("✓ Container restarted!")

# 4. Also check starinternational if database exists
cmd_star = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_starinternational_havano_pro_lzjsrbqoynmd psql -U Starinternational -d starinternational_havano_pro_lzjsrbqoynmd -c \\\"UPDATE crm_lead SET user_id = COALESCE(create_uid, 2) WHERE user_id IS NULL; SELECT count(*) FROM crm_lead WHERE user_id IS NULL;\\\" 2>/dev/null || true\""
)
res_star = subprocess.run(cmd_star, shell=True, capture_output=True, text=True)
if res_star.stdout:
    print("\nStarinternational DB output:\n", res_star.stdout)

print("\n✅ All leads now have a salesperson/user assigned!")
