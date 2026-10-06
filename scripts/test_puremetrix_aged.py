import subprocess

code = """
import odoo
import odoo.tools.config
import odoo.api

odoo.tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'puremetrix_havano_pro_obgntonlpukagjiluzh'])
registry = odoo.registry('puremetrix_havano_pro_obgntonlpukagjiluzh')
with registry.cursor() as cr:
    env = odoo.api.Environment(cr, odoo.SUPERUSER_ID, {})
    
    # 1. Test Aged Receivable report
    aged_rec_report = env.ref('account_reports.aged_receivable_report', raise_if_not_found=False)
    if aged_rec_report:
        options = aged_rec_report._get_options({'unfold_all': True})
        lines = aged_rec_report._get_lines(options)
        print(f"Total Aged Receivable lines: {len(lines)}")
        for l in lines[:15]:
            print("  ", l.get('name'), "--> id:", l.get('id'))
            
    # 2. Test Aged Payable report
    aged_pay_report = env.ref('account_reports.aged_payable_report', raise_if_not_found=False)
    if aged_pay_report:
        options = aged_pay_report._get_options({'unfold_all': True})
        lines = aged_pay_report._get_lines(options)
        print(f"\nTotal Aged Payable lines: {len(lines)}")
        for l in lines[:15]:
            print("  ", l.get('name'), "--> id:", l.get('id'))
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec odoo_puremetrix_havano_pro_obgntonlpukagjiluzh python3 -c {repr(code)}\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=40)
print("OUT:\n", res.stdout)
print("ERR:\n", res.stderr)
