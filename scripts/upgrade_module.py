import xmlrpc.client

url = "http://localhost:9060"
db = "showline_s2_havano_pro_xcynznxmwcotukbxkm"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, "admin", "Admin@Odoo1234!", {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

with open("/opt/odoo-secure/addons-custom/crm_import/views/crm_activity_log_views.xml", "r") as f:
    act_xml = f.read()

with open("/opt/odoo-secure/addons-custom/crm_import/views/crm_lead_views.xml", "r") as f:
    lead_xml = f.read()

# Parse the inner arch from XML files or upgrade module via odoo
# Let's upgrade crm_import module cleanly!
module_id = models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.module.module", "search", [[("name", "=", "crm_import")]])
if module_id:
    print("Upgrading crm_import module...")
    models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.module.module", "button_immediate_upgrade", [module_id])
    print("Module upgraded successfully!")
