import subprocess
import os

def run(cmd, cwd=None):
    print(f"\n--- Running: {cmd} in {cwd} ---")
    res = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    print("STDOUT:")
    print(res.stdout)
    print("STDERR:")
    print(res.stderr)
    print(f"Exit code: {res.returncode}")
    return res.returncode

# 1. crm_import
crm_path = "/opt/odoo-secure/addons-custom/crm_import"
run("git status", cwd=crm_path)
run("git remote -v", cwd=crm_path)
run("git log -n 3 --oneline", cwd=crm_path)

# Add all relevant crm_import changes and commit
run("git add .", cwd=crm_path)
run('git commit -m "feat(crm): hourly activity log tracking and timetable view"', cwd=crm_path)
run("git push origin main", cwd=crm_path)

# 2. havano_all_in_one
havano_path = "/opt/odoo-secure/addons-custom/havano_all_in_one"
if os.path.exists(havano_path):
    run("git status", cwd=havano_path)
    run("git remote -v", cwd=havano_path)
    run("git log -n 3 --oneline", cwd=havano_path)
    run("git add reports/trucking_invoice_templates.xml", cwd=havano_path)
    run('git commit -m "fix(reports): reverse FROM and INVOICE TO on trucking customer invoice"', cwd=havano_path)
    run("git push origin main", cwd=havano_path)

# 3. Check /home/starinternational_havano_pro_lzjsrbqoynmd/custom-addons/trucking if it's a git repo
trucking_path = "/home/starinternational_havano_pro_lzjsrbqoynmd/custom-addons/trucking"
if os.path.exists(trucking_path):
    run("git status", cwd=trucking_path)
