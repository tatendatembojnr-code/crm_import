import subprocess
import os

with open("/tmp/git_result.txt", "w") as out:
    def log(msg):
        out.write(msg + "\n")
        out.flush()

    log("=== Testing SSH connection to GitHub ===")
    res = subprocess.run(
        ["ssh", "-o", "StrictHostKeyChecking=no", "-T", "git@github.com"],
        capture_output=True, text=True, timeout=10
    )
    log(f"SSH returncode: {res.returncode}")
    log(f"SSH stdout: {res.stdout}")
    log(f"SSH stderr: {res.stderr}")

    # Check git push for crm_import with SSH URL
    crm_path = "/opt/odoo-secure/addons-custom/crm_import"
    log("=== Setting SSH remote for crm_import ===")
    subprocess.run(["git", "remote", "set-url", "origin", "git@github.com:tatendatembojnr-code/crm_import.git"], cwd=crm_path)
    
    # Try push
    log("=== Pushing crm_import ===")
    res_push = subprocess.run(["git", "push", "origin", "main"], cwd=crm_path, capture_output=True, text=True, timeout=30)
    log(f"crm_import push stdout: {res_push.stdout}")
    log(f"crm_import push stderr: {res_push.stderr}")
    log(f"crm_import push code: {res_push.returncode}")

    # For havano_all_in_one
    havano_path = "/opt/odoo-secure/addons-custom/havano_all_in_one"
    log("=== Setting SSH remote for havano_all_in_one ===")
    subprocess.run(["git", "remote", "set-url", "origin", "git@github.com:draftpos/havano_all_in_one.git"], cwd=havano_path)
    
    log("=== Staging & Committing havano_all_in_one ===")
    subprocess.run(["git", "add", "reports/trucking_invoice_templates.xml"], cwd=havano_path)
    res_commit = subprocess.run(["git", "commit", "-m", "fix(reports): reverse FROM and INVOICE TO on trucking customer invoice"], cwd=havano_path, capture_output=True, text=True)
    log(f"havano_all_in_one commit stdout: {res_commit.stdout}")
    log(f"havano_all_in_one commit stderr: {res_commit.stderr}")

    log("=== Pushing havano_all_in_one ===")
    res_push2 = subprocess.run(["git", "push", "origin", "main"], cwd=havano_path, capture_output=True, text=True, timeout=30)
    log(f"havano_all_in_one push stdout: {res_push2.stdout}")
    log(f"havano_all_in_one push stderr: {res_push2.stderr}")
    log(f"havano_all_in_one push code: {res_push2.returncode}")
