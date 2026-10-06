import subprocess

code = """
import odoo
import odoo.tools.config
import odoo.api

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm'])
registry = odoo.registry('showline_s2_havano_pro_xcynznxmwcotukbxkm')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    res = env['crm.lead'].web_read_group([], ['user_id'], ['__count'])
    print('GROUPS COUNT:', len(res['groups']))
    print('SAMPLE GROUP:', res['groups'][0] if res['groups'] else 'None')
    print('SUCCESS_VERIFIED')
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm python3 -c {repr(code)}\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
