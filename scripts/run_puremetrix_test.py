import subprocess

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec odoo_puremetrix_havano_pro_obgntonlpukagjiluzh python3 /mnt/extra-addons/havano_all_in_one/test_aged.py\""
)
res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
print("OUT:\n", res.stdout)
print("ERR:\n", res.stderr)
