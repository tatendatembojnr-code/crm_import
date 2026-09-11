import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()
cr.execute("SELECT id, model FROM ir_model WHERE model = 'crm.lead';")
print("ir_model for crm.lead:", cr.fetchone())
