import subprocess
import time

print("1. Syncing template to starinternational custom-addons...")
cmd_sync = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"cp /opt/odoo-secure/addons-custom/havano_all_in_one/reports/trucking_invoice_templates.xml /home/starinternational_havano_pro_lzjsrbqoynmd/custom-addons/havano_all_in_one/reports/trucking_invoice_templates.xml\""
)
subprocess.run(cmd_sync, shell=True, check=True)
print("✓ Synced template file!")

print("2. Marking havano_all_in_one to upgrade in starinternational DB...")
cmd_db = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec psql_starinternational_havano_pro_lzjsrbqoynmd psql -U Showline -d starinternational_havano_pro_lzjsrbqoynmd -c \\\"UPDATE ir_module_module SET state='to upgrade' WHERE name='havano_all_in_one';\\\"\""
)
subprocess.run(cmd_db, shell=True, check=True)
print("✓ Marked module to upgrade!")

print("3. Restarting starinternational Odoo container...")
cmd_restart = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker restart odoo_starinternational_havano_pro_lzjsrbqoynmd\""
)
subprocess.run(cmd_restart, shell=True, check=True)
print("✓ Restarted container!")

time.sleep(12)

print("4. Checking upgrade status in logs...")
cmd_logs = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker logs --tail 30 odoo_starinternational_havano_pro_lzjsrbqoynmd\""
)
res = subprocess.run(cmd_logs, shell=True, capture_output=True, text=True)
print("Logs:\n", res.stdout)
