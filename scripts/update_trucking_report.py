import psycopg2
import subprocess
import xml.etree.ElementTree as ET
import json

print("1. Syncing files...")
cmd_sync = [
    "sshpass", "-p", "Farai@#$1234", "ssh", 
    "-o", "StrictHostKeyChecking=no", 
    "-o", "UserKnownHostsFile=/dev/null", 
    "root@127.0.0.1",
    "rsync -av /opt/odoo-secure/addons-custom/havano_all_in_one/ /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/havano_all_in_one/"
]
res = subprocess.run(cmd_sync, capture_output=True, text=True)
print("Sync output:", res.stdout, res.stderr)

cmd_script = """
import psycopg2
import xml.etree.ElementTree as ET
import json

conn = psycopg2.connect(
    dbname="showline_s2_havano_pro_xcynznxmwcotukbxkm",
    user="Showline",
    password="Showline@#$1234",
    host="db",
    port=5432
)
conn.autocommit = True
cr = conn.cursor()

cr.execute(\"\"\"
    SELECT v.id, v.key, v.name, v.arch_db 
    FROM ir_ui_view v 
    JOIN ir_model_data d ON d.res_id = v.id AND d.model = 'ir.ui.view'
    WHERE d.module = 'havano_all_in_one' AND d.name = 'custom_template_report_bill_trucking';
\"\"\")
row = cr.fetchone()
print("Found view:", row[0], row[1], row[2])

with open("/mnt/extra-addons/havano_all_in_one/reports/trucking_invoice_templates.xml", "r") as f:
    xml_content = f.read()

root = ET.fromstring(xml_content)
template_elem = root.find(".//template[@id='custom_template_report_bill_trucking']")
if template_elem is not None:
    template_elem.tag = "t"
    template_elem.set("t-name", "havano_all_in_one.custom_template_report_bill_trucking")
    if "id" in template_elem.attrib:
        del template_elem.attrib["id"]
    new_arch = ET.tostring(template_elem, encoding="unicode")
    print("New arch constructed (len:", len(new_arch), ")")
    
    new_arch_db = {"en_US": new_arch}
    cr.execute("UPDATE ir_ui_view SET arch_db = %s::jsonb WHERE id = %s", (json.dumps(new_arch_db), row[0]))
    print("✓ Successfully updated ir_ui_view arch_db!")

cr.execute("UPDATE ir_module_module SET state='to upgrade' WHERE name='havano_all_in_one';")
print("✓ Marked module to upgrade in DB")
"""

import subprocess

# Write script to file in container and execute
write_cmd = [
    "sshpass", "-p", "Farai@#$1234", "ssh", 
    "-o", "StrictHostKeyChecking=no", 
    "-o", "UserKnownHostsFile=/dev/null", 
    "root@127.0.0.1",
    f"docker exec -i odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm python3 -c {subprocess.list2cmdline([cmd_script])}"
]
print("Running db update inside odoo container...")
res = subprocess.run(write_cmd, capture_output=True, text=True)
print("DB script output:\n", res.stdout)
if res.stderr:
    print("DB script stderr:\n", res.stderr)

print("3. Restarting Odoo container...")
cmd_restart = [
    "sshpass", "-p", "Farai@#$1234", "ssh", 
    "-o", "StrictHostKeyChecking=no", 
    "-o", "UserKnownHostsFile=/dev/null", 
    "root@127.0.0.1",
    "docker restart odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm"
]
subprocess.run(cmd_restart, check=True)
print("✓ Restarted container!")

