import subprocess
import os

with open("/tmp/auth_check.txt", "w") as out:
    def log(msg):
        out.write(msg + "\n")
        out.flush()

    def run_as_root(cmd):
        ssh_cmd = [
            "sshpass", "-p", "Farai@#$1234",
            "ssh", "-o", "StrictHostKeyChecking=no", "root@127.0.0.1",
            cmd
        ]
        res = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=15)
        return res.stdout, res.stderr, res.returncode

    log("=== Root SSH Keys & Git Config ===")
    stdout, stderr, rc = run_as_root("ls -la /root/.ssh; ls -la /root/.git*; git config --global --list")
    log(f"stdout: {stdout}")
    log(f"stderr: {stderr}")

    log("=== Fix permissions on havano_all_in_one ===")
    stdout, stderr, rc = run_as_root("chown -R ttembo:ttembo /opt/odoo-secure/addons-custom/havano_all_in_one; chmod -R 775 /opt/odoo-secure/addons-custom/havano_all_in_one")
    log(f"chmod stdout: {stdout}")

    log("=== Check root SSH GitHub connection ===")
    stdout, stderr, rc = run_as_root("ssh -o StrictHostKeyChecking=no -T git@github.com")
    log(f"root ssh github stdout: {stdout}")
    log(f"root ssh github stderr: {stderr}")

    log("=== Check git credentials on system ===")
    stdout, stderr, rc = run_as_root("find /root /home -name '.git-credentials' -o -name '.gitconfig' -o -name 'config' 2>/dev/null")
    log(f"find configs: {stdout}")
