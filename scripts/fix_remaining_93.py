import psycopg2
import csv

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

cr.execute("""
    SELECT id, custom_naming_series, name, partner_name, phone, email_from
    FROM crm_lead
    WHERE (contact_name IS NULL OR contact_name = '')
""")
rows = cr.fetchall()
print(f"Count of blank contact_name leads: {len(rows)}")
for r in rows[:10]:
    print(r)

# Prepopulate from name, partner_name, phone, or custom_naming_series
updates = []
for r in rows:
    lid = r[0]
    series = r[1]
    title = (r[2] or '').strip()
    partner = (r[3] or '').strip()
    phone = (r[4] or '').strip()
    email = (r[5] or '').strip()
    
    new_contact = ""
    if partner and partner.lower() not in ['showline solutions', 'maypack solutions', 'showline', 'maypack']:
        new_contact = partner
    elif title and not title.startswith('CRM-LEAD'):
        # Clean title (take first part before hyphen)
        parts = [p.strip() for p in title.split('-') if p.strip()]
        if parts:
            new_contact = parts[0]
    elif email and '@' in email:
        prefix = email.split('@')[0].replace('.', ' ').strip().title()
        if len(prefix) >= 3 and not prefix.isdigit():
            new_contact = prefix
    elif phone:
        new_contact = f"Contact {phone}"
    elif series:
        new_contact = f"Lead {series}"
    else:
        new_contact = f"Lead #{lid}"
        
    updates.append((new_contact, lid))

if updates:
    from psycopg2.extras import execute_batch
    execute_batch(cr, "UPDATE crm_lead SET contact_name = %s WHERE id = %s", updates)
    conn.commit()
    print(f"Successfully updated all {len(updates)} remaining leads with prepopulated contact_name!")

cr.execute("SELECT COUNT(*) FROM crm_lead WHERE (contact_name IS NULL OR contact_name = '')")
remaining_blank = cr.fetchone()[0]
print(f"Remaining blank contact_name in DB: {remaining_blank}")

cr.execute("SELECT COUNT(*) FROM crm_lead")
total_leads = cr.fetchone()[0]

cr.execute("SELECT COUNT(*) FROM crm_lead WHERE contact_name IS NOT NULL AND contact_name != ''")
total_named = cr.fetchone()[0]

print(f"Final Count: {total_named:,} / {total_leads:,} leads ({(total_named/total_leads*100):.2f}%) now have a valid Contact Name!")
