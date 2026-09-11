import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
conn.autocommit = True
cr = conn.cursor()

cr.execute("SELECT state, latest_version FROM ir_module_module WHERE name = 'crm_import'")
row = cr.fetchone()
print("crm_import module status:", row)

# Set to upgrade so Odoo updates models, tables, and views on restart
cr.execute("UPDATE ir_module_module SET state = 'to upgrade' WHERE name = 'crm_import'")
print("Marked crm_import as 'to upgrade'.")

cr.execute("SELECT model, name FROM ir_model WHERE model = 'crm.product'")
m = cr.fetchone()
print("crm.product in ir_model:", m)
