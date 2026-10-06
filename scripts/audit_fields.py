import psycopg2

conn = psycopg2.connect(dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm', user='Showline', password='Showline@#$1234', host='db', port=5432)
cr = conn.cursor()

cr.execute("""
    SELECT 
        COUNT(*) as total,
        COUNT(CASE WHEN contact_name IS NOT NULL AND contact_name != '' THEN 1 END) as with_contact,
        COUNT(CASE WHEN partner_name IS NOT NULL AND partner_name != '' THEN 1 END) as with_company,
        COUNT(CASE WHEN custom_product IS NOT NULL AND custom_product != '' THEN 1 END) as with_product_str,
        COUNT(CASE WHEN crm_product_id IS NOT NULL THEN 1 END) as with_product_rel,
        COUNT(CASE WHEN phone IS NOT NULL AND phone != '' THEN 1 END) as with_phone,
        COUNT(CASE WHEN email_from IS NOT NULL AND email_from != '' THEN 1 END) as with_email,
        COUNT(CASE WHEN user_id IS NOT NULL THEN 1 END) as with_owner,
        COUNT(CASE WHEN create_date IS NOT NULL THEN 1 END) as with_date,
        COUNT(CASE WHEN custom_deal_size > 0 THEN 1 END) as with_deal_size
    FROM crm_lead;
""")
row = cr.fetchone()
print(f"Total Leads in DB:          {row[0]:,}")
print(f"With Contact Name:          {row[1]:,} ({(row[1]/row[0]*100):.1f}%)")
print(f"With Company/Partner Name: {row[2]:,} ({(row[2]/row[0]*100):.1f}%)")
print(f"With Product Interest:      {row[3]:,} ({(row[3]/row[0]*100):.1f}%)")
print(f"With Linked CRM Product:    {row[4]:,} ({(row[4]/row[0]*100):.1f}%)")
print(f"With Phone / Mobile:        {row[5]:,} ({(row[5]/row[0]*100):.1f}%)")
print(f"With Email:                 {row[6]:,} ({(row[6]/row[0]*100):.1f}%)")
print(f"With Assigned Salesperson:  {row[7]:,} ({(row[7]/row[0]*100):.1f}%)")
print(f"With Creation Date:         {row[8]:,} ({(row[8]/row[0]*100):.1f}%)")
print(f"With Deal Size > 0:         {row[9]:,} ({(row[9]/row[0]*100):.1f}%)")
