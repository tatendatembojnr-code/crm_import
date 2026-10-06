import subprocess

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    "\"docker exec odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm odoo shell -c /etc/odoo/odoo.conf -d showline_s2_havano_pro_xcynznxmwcotukbxkm --no-http << 'EOF'\n"
    "res = env['crm.lead'].web_read_group([], ['user_id'], ['__count'])\n"
    "print('web_read_group by user_id SUCCESS:', res)\n"
    "EOF\""
)

print("Running test inside odoo shell...")
proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", proc.stdout)
print("STDERR:\n", proc.stderr)
