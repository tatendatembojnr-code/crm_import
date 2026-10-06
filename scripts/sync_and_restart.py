import subprocess
import time

print("1. Syncing all addon files to container custom-addons folder...")
cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"rsync -av --delete /opt/odoo-secure/addons-custom/crm_import/ /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/crm_import/\""
)
subprocess.run(cmd, shell=True, check=True)
print("✓ Synced files!")

print("\n2. Setting ir_module_module to 'to upgrade'...")
cmd_db = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"UPDATE ir_module_module SET state='to upgrade' WHERE name='crm_import';\\\"\""
)
subprocess.run(cmd_db, shell=True, check=True)
print("✓ Marked module to upgrade!")

print("\n3. Restarting Odoo container to trigger module upgrade...")
cmd_restart = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker restart odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm\""
)
subprocess.run(cmd_restart, shell=True, check=True)
print("✓ Container restarted!")

time.sleep(12)

print("\n4. Checking Odoo logs to verify upgrade status...")
cmd_logs = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker logs --tail 30 odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm\""
)
res = subprocess.run(cmd_logs, shell=True, capture_output=True, text=True)
print(res.stdout)
if res.stderr:
    print(res.stderr)

print("\n✅ Finished!")
