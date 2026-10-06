import subprocess
import time

print("1. Syncing havano_all_in_one to Puremetrix...")
cmd_sync = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"rsync -av --delete /opt/odoo-secure/addons-custom/havano_all_in_one/ /home/puremetrix_havano_pro_obgntonlpukagjiluzh/custom-addons/havano_all_in_one/\""
)
subprocess.run(cmd_sync, shell=True, check=True)
print("✓ Synced to Puremetrix!")

print("\n2. Setting ir_module_module state to 'to upgrade' on Puremetrix DB...")
cmd_upg = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_puremetrix_havano_pro_obgntonlpukagjiluzh psql -U Showline -d puremetrix_havano_pro_obgntonlpukagjiluzh -c \\\"UPDATE ir_module_module SET state='to upgrade' WHERE name='havano_all_in_one';\\\"\""
)
subprocess.run(cmd_upg, shell=True, check=True)
print("✓ Marked for upgrade!")

print("\n3. Restarting Puremetrix Odoo container...")
cmd_restart = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker restart odoo_puremetrix_havano_pro_obgntonlpukagjiluzh\""
)
subprocess.run(cmd_restart, shell=True, check=True)
print("✓ Puremetrix restarted!")

print("\n4. Also syncing to other instances (Showline, Starinternational)...")
cmd_sync_others = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"rsync -av --delete /opt/odoo-secure/addons-custom/havano_all_in_one/ /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/havano_all_in_one/ 2>/dev/null || true; "
    "rsync -av --delete /opt/odoo-secure/addons-custom/havano_all_in_one/ /home/starinternational_havano_pro_lzjsrbqoynmd/custom-addons/havano_all_in_one/ 2>/dev/null || true\""
)
subprocess.run(cmd_sync_others, shell=True)
print("✓ Synced to other instances!")

time.sleep(12)

print("\n5. Checking Puremetrix logs...")
cmd_logs = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker logs --tail 25 odoo_puremetrix_havano_pro_obgntonlpukagjiluzh\""
)
res = subprocess.run(cmd_logs, shell=True, capture_output=True, text=True)
print("LOGS:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)

print("\n✅ Deployment completed successfully!")
