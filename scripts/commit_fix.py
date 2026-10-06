import subprocess

cmd = "git -C /opt/odoo-secure/addons-custom/crm_import add . && git -C /opt/odoo-secure/addons-custom/crm_import commit -m 'fix(crm): fix web_read_group return and auto-assign user_id on lead creation'"
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:", res.stdout)
print("STDERR:", res.stderr)
