import csv
import os
import sys
import re
import urllib.request
import json
import psycopg2
import html

# Google Drive Download Helper
def download_gdrive_file(file_id, output_path):
    print(f"Downloading Google Drive file ID: {file_id} to {output_path}...")
    # Base URL for Google Drive file export / download
    url = f"https://drive.usercontent.google.com/download?id={file_id}&export=download&confirm=t"
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as resp, open(output_path, 'wb') as out_file:
            data = resp.read()
            out_file.write(data)
        print(f"  Downloaded {os.path.getsize(output_path):,} bytes.")
        return True
    except Exception as e:
        print(f"  Direct download error: {e}. Trying alternative download endpoint...")
        alt_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        req2 = urllib.request.Request(alt_url, headers={'User-Agent': 'Mozilla/5.0'})
        try:
            with urllib.request.urlopen(req2) as resp, open(output_path, 'wb') as out_file:
                out_file.write(resp.read())
            print(f"  Downloaded {os.path.getsize(output_path):,} bytes via alt endpoint.")
            return True
        except Exception as e2:
            print(f"  Failed to download {file_id}: {e2}")
            return False

def parse_frappe_csv(filepath):
    with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
        reader = list(csv.reader(f))
    
    if not reader:
        return [], []
        
    headers = None
    data_start = 0
    is_template = False
    
    for i, row in enumerate(reader):
        first = str(row[0]).strip() if row and row[0] else ""
        if first == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start = i + 5
            is_template = True
            break
            
    if not is_template:
        headers = [str(c).strip() if c is not None else "" for c in reader[0]]
        data_start = 1
        
    records = []
    col_offset = 1 if is_template else 0
    
    for row in reader[data_start:]:
        if not any(row):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            if h == '~': break
            if h and h not in row_dict:
                col = idx + col_offset
                row_dict[h] = row[col] if col < len(row) else None
        records.append(row_dict)
        
    return headers, records

path_1 = '/tmp/drive1.csv'
path_2 = '/tmp/drive2.csv'

id_1 = "10E158wQrxm3pYSsXoxQbfRA9dB_UZ_Cq (Lead(10).csv)"
id_2 = "1GbLubkJCO-_R842x_H0vwHAtFd5hL068 (ToDo(10).csv)"

headers_1, recs_1 = parse_frappe_csv(path_1)
headers_2, recs_2 = parse_frappe_csv(path_2)

print(f"\n--- File 1 Inspection ({id_1}) ---")
print(f"Total Rows: {len(recs_1):,}")
print(f"Headers Sample: {headers_1[:12] if headers_1 else 'None'}")
first_1 = recs_1[0] if recs_1 else {}
print(f"Keys: {list(first_1.keys())[:10]}")

print(f"\n--- File 2 Inspection ({id_2}) ---")
print(f"Total Rows: {len(recs_2):,}")
print(f"Headers Sample: {headers_2[:12] if headers_2 else 'None'}")
first_2 = recs_2[0] if recs_2 else {}
print(f"Keys: {list(first_2.keys())[:10]}")

# Connect to database
conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

def verify_leads(records, label):
    print("\n" + "="*80)
    print(f"VERIFYING LEADS FILE: {label} ({len(records):,} records)")
    print("="*80)
    
    cr.execute("""
        SELECT 
            cl.custom_naming_series,
            cl.id,
            cl.name,
            cl.contact_name,
            cl.partner_name,
            cl.phone,
            cl.email_from,
            cl.stage_id,
            cl.expected_revenue,
            cl.custom_deal_size,
            cl.create_date,
            cl.legacy_create_date,
            ru.login
        FROM crm_lead cl
        LEFT JOIN res_users ru ON cl.user_id = ru.id
        WHERE cl.custom_naming_series IS NOT NULL
    """)
    db_leads = {}
    for r in cr.fetchall():
        db_leads[r[0]] = {
            'id': r[1],
            'name': r[2],
            'contact_name': r[3],
            'partner_name': r[4],
            'phone': r[5],
            'email': r[6],
            'stage_id': r[7],
            'expected_revenue': r[8],
            'deal_size': r[9],
            'create_date': r[10],
            'legacy_create_date': r[11],
            'owner_login': r[12]
        }
    
    matched = 0
    missing = []
    with_contact_name = 0
    blank_contact_name = 0
    phone_matched = 0
    email_matched = 0
    
    for r in records:
        lid = (r.get('ID') or r.get('name') or r.get('id') or '').strip().strip('"')
        if not lid: continue
        
        if lid in db_leads:
            matched += 1
            rec = db_leads[lid]
            if rec['contact_name'] and rec['contact_name'].strip():
                with_contact_name += 1
            else:
                blank_contact_name += 1
                
            csv_phone = (r.get('Mobile No') or r.get('mobile_no') or r.get('Phone') or r.get('phone') or '').strip()
            if csv_phone and rec['phone']:
                phone_matched += 1
                
            csv_email = (r.get('Email') or r.get('email_id') or r.get('email') or '').strip().lower()
            if csv_email and rec['email']:
                email_matched += 1
        else:
            missing.append(lid)
            
    print(f"Total Leads in CSV:          {len(records):,}")
    print(f"Total Leads in Database:     {len(db_leads):,}")
    print(f"Matched Leads:               {matched:,} / {len(records):,} ({(matched/len(records)*100 if records else 0):.2f}%)")
    print(f"Leads with Contact Name:     {with_contact_name:,} / {matched:,} ({(with_contact_name/matched*100 if matched else 0):.2f}%)")
    print(f"Leads with Blank Contact:    {blank_contact_name:,}")
    if missing:
        print(f"Missing Leads ({len(missing)}): {missing[:10]}")
    else:
        print("✓ ALL leads from this CSV exist in the Odoo database!")

def verify_todos(records, label):
    print("\n" + "="*80)
    print(f"VERIFYING TO-DOS FILE: {label} ({len(records):,} records)")
    print("="*80)
    
    cr.execute("""
        SELECT 
            COALESCE(t.legacy_id, t.name) as lookup_id,
            t.id,
            t.name,
            t.status,
            t.allocated_to,
            t.lead_id,
            t.date,
            t.create_date,
            cl.custom_naming_series
        FROM todo_task t
        LEFT JOIN crm_lead cl ON t.lead_id = cl.id
    """)
    db_todos = {}
    for r in cr.fetchall():
        if r[0]:
            db_todos[r[0]] = {
                'id': r[1],
                'name': r[2],
                'status': r[3],
                'allocated_to': r[4],
                'lead_id': r[5],
                'date': r[6],
                'create_date': r[7],
                'lead_series': r[8]
            }
            
    cr.execute("SELECT COUNT(*) FROM mail_activity WHERE res_model = 'crm.lead'")
    open_act_count = cr.fetchone()[0]
    
    matched = 0
    missing = []
    linked_to_lead = 0
    
    for r in records:
        tid = (r.get('ID') or r.get('name') or r.get('id') or '').strip().strip('"')
        if not tid: continue
        
        if tid in db_todos:
            matched += 1
            if db_todos[tid]['lead_id']:
                linked_to_lead += 1
        else:
            missing.append(tid)
            
    print(f"Total To-Dos in CSV:         {len(records):,}")
    print(f"Total To-Dos in Database:    {len(db_todos):,}")
    print(f"Matched To-Dos:              {matched:,} / {len(records):,} ({(matched/len(records)*100 if records else 0):.2f}%)")
    print(f"Linked to CRM Leads:         {linked_to_lead:,} / {matched:,}")
    print(f"CRM Mail Activities in DB:   {open_act_count:,}")
    if missing:
        print(f"Missing To-Dos ({len(missing)}): {missing[:10]}")
    else:
        print("✓ ALL To-Dos from this CSV exist in the Odoo database!")

# Detect file types
for f_idx, (headers, recs, file_id) in enumerate([(headers_1, recs_1, id_1), (headers_2, recs_2, id_2)], start=1):
    first_row = recs[0] if recs else {}
    if 'lead_name' in first_row or 'First Name' in first_row or 'custom_deal_size_' in first_row or 'Organization/Store  Name' in first_row:
        verify_leads(recs, f"File {f_idx} (Google Drive ID: {file_id})")
    elif 'reference_name' in first_row or 'reference_type' in first_row or 'allocated_to' in first_row or 'description' in first_row:
        verify_todos(recs, f"File {f_idx} (Google Drive ID: {file_id})")
    elif 'Email' in first_row and 'Role Profile' in first_row:
        print(f"File {f_idx} is Users CSV")
    else:
        print(f"File {f_idx} headers: {list(first_row.keys())[:10]}")
        # Try both or inspect
        if any('lead' in str(k).lower() for k in first_row.keys()):
            verify_leads(recs, f"File {f_idx} (Google Drive ID: {file_id})")
        else:
            verify_todos(recs, f"File {f_idx} (Google Drive ID: {file_id})")

print("\n" + "="*80)
print("VERIFICATION SCRIPT FINISHED")
print("="*80)
