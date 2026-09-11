import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("SELECT count(*) FROM crm_lead;")
total_leads = cr.fetchone()[0]

cr.execute("SELECT count(*) FROM crm_lead WHERE street IS NOT NULL AND street != '';")
leads_with_street = cr.fetchone()[0]

cr.execute("SELECT count(*) FROM crm_lead WHERE description IS NOT NULL AND description != '';")
leads_with_desc = cr.fetchone()[0]

cr.execute("SELECT count(*) FROM crm_lead WHERE city IS NOT NULL AND city != '';")
leads_with_city = cr.fetchone()[0]

print(f"Total Leads in DB: {total_leads:,}")
print(f"Leads with Street (Full Address) in DB: {leads_with_street:,}")
print(f"Leads with Description (Notes) in DB: {leads_with_desc:,}")
print(f"Leads with City in DB: {leads_with_city:,}")

cr.execute("SELECT id, name, custom_naming_series, street, city, description FROM crm_lead WHERE custom_naming_series = 'Lead014995';")
print("\nLead014995 status in DB:", cr.fetchone())

