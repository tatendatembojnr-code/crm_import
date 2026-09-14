import xmlrpc.client

url = "http://localhost:9060"
db = "showline_s2_havano_pro_xcynznxmwcotukbxkm"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, "admin", "Admin@Odoo1234!", {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

# We can trigger init on crm.activity.log by calling init() or upgrade module
print("Upgrading crm_import module to recreate SQL view cleanly...")
module_ids = models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.module.module", "search", [[("name", "=", "crm_import")]])
models.execute_kw(db, uid, "Admin@Odoo1234!", "ir.module.module", "button_immediate_upgrade", [module_ids])
print("Module upgraded!")
