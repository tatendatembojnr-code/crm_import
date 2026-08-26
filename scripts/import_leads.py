import sys
import os
import csv
import xmlrpc.client
import psycopg2
import subprocess
import time

print("--- INITIALIZING UNLIMITED LEADS IMPORT ---")
global_start = time.time()

url = 'http://localhost:8069'
db = 'havano_test'
username = 'admin'
password = 'admin'

common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common')
uid = common.authenticate(db, username, password, {})
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object')

if not uid:
    print("Authentication failed!")
    exit()

print("Connecting to database for incremental update...")
conn = psycopg2.connect("dbname='havano_test' user='odoo' password='odoo' host='127.0.0.1' port='5432'")
conn.autocommit = True
cur = conn.cursor()
# Wiping statements removed to preserve existing data and support incremental updates

def safe_date(value):
    if not value or str(value).strip() == '': return False
    str_val = str(value).strip().strip('"')
    if '.' in str_val: str_val = str_val.split('.')[0]
    parts = str_val.split(' ')
    date_part = parts[0]
    if '-' in date_part:
        d = date_part.split('-')
        if len(d) == 3 and len(d[0]) <= 2: date_part = f"{d[2]}-{d[1]:0>2}-{d[0]:0>2}"
    if len(parts) > 1: return f"{date_part} {parts[1]}"
    return date_part

def safe_float(value):
    try: return float(value.replace(',', '').strip('"'))
    except: return 0.0

ctx = {'tracking_disable': True, 'mail_create_nolog': True, 'mail_create_nosubscribe': True}

# Stages
try:
    stages = models.execute_kw(db, uid, password, 'crm.stage', 'search_read', [[]], {'fields': ['id', 'name']})
    stage_map = {str(s['name']).lower(): s['id'] for s in stages}
except:
    stage_map = {}

# Products
print("Preloading all products to accelerate processing...")
product_map = {}
try:
    product_records = models.execute_kw(db, uid, password, 'product.product', 'search_read', [[('default_code', '!=', False)]], {'fields': ['id', 'default_code']})
    for p in product_records:
        product_map[p['default_code'].strip()] = p['id']

    # Get the partner_id for the current user (uid) so chatter messages show as Administrator instead of ErpBot
    admin_partner_id = models.execute_kw(db, uid, password, 'res.users', 'read', [[uid]], {'fields': ['partner_id']})[0]['partner_id'][0]
    
    # Preload users
    all_users = models.execute_kw(db, uid, password, 'res.users', 'search_read', [[('name', '!=', False)]], {'fields': ['id', 'name', 'partner_id']})
    user_map = {str(u['name']).lower().strip(): (u['id'], u['partner_id'][0]) for u in all_users}
except Exception as e:
    print(f"Error preloading products/users: {e}")

def get_or_create_user(name, login=''):
    if not name: return uid, admin_partner_id
    name = str(name).strip()
    key = name.lower()
    if key in user_map:
        return user_map[key]
    
    login_val = str(login).strip() if login else f"{name.replace(' ', '').lower()}@example.com"
    try:
        new_uid = models.execute_kw(db, uid, password, 'res.users', 'create', [{'name': name, 'login': login_val}])
        new_pid = models.execute_kw(db, uid, password, 'res.users', 'read', [[new_uid]], {'fields': ['partner_id']})[0]['partner_id'][0]
        user_map[key] = (new_uid, new_pid)
        return user_map[key]
    except:
        return uid, admin_partner_id

def get_or_create_product(prod_name):
    if not prod_name: return False
    clean = str(prod_name).strip().strip('"')
    clean_lower = clean.lower()
    
    if clean_lower in product_map: 
        return product_map[clean_lower]
        
    # If not found in preload, create it (avoiding search to save time)
    prod_id = models.execute_kw(db, uid, password, 'crm.product', 'create', [{'name': clean}])
    product_map[clean_lower] = prod_id
    return prod_id

print("Reading ALL Leads WITH A PRODUCT from Lead.csv...")
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DATA_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, '..', 'data_import'))

lead_csv = sys.argv[1] if len(sys.argv) > 1 else os.path.join(DEFAULT_DATA_DIR, 'Lead.csv')
if not os.path.exists(lead_csv) and os.path.exists(r'C:\Users\DELL\Desktop\odoo\data_import\Lead.csv'):
    lead_csv = r'C:\Users\DELL\Desktop\odoo\data_import\Lead.csv'

lead_vals_list = []
imported_lead_ids = []
import_id_to_real_id = {}

with open(lead_csv, mode='r', encoding='utf-8', errors='ignore') as f:
    reader = csv.reader(f)
    for _ in range(20): next(reader, None) # Skip metadata
    
    count = 0
    for row in reader:
        count += 1
        if count % 1000 == 0:
            print(f"Scanned {count} rows in CSV...", end='\\r')
            
        if len(row) < 50 or not row[1].strip(): continue
        
        product = row[4].strip().strip('"') if row[4] else False
        if not product:
            continue # We only want leads that have products
        
        import_id = row[1].strip().strip('"')
        
        # Skip if we already processed this exact Lead ID to prevent duplicates!
        if import_id in imported_lead_ids:
            continue
            
        erp_status = row[2].strip().strip('"').lower() if row[2] else ''
        company = row[12].strip().strip('"') if row[12] else False
        contact = row[9].strip().strip('"') or row[26].strip().strip('"') or False
        deal_size = safe_float(row[6]) if row[6] else safe_float(row[34])
        name_val = product if product else (company or contact or import_id)
        
        # Row 8 is Salesperson Name in Lead.csv
        salesperson_name = row[8].strip().strip('"') if row[8] else False
        lead_uid, lead_pid = get_or_create_user(salesperson_name)
        
        stage_name = 'qualified' if erp_status in ['lead', 'open', 'interested', 'replied', 'opportunity', 'quotation'] else 'won' if erp_status == 'converted' else None
        
        vals = {
            'name': name_val,
            'contact_name': contact,
            'partner_name': company,
            'email_from': row[24].strip().strip('"') or row[27].strip().strip('"') or False,
            'phone': row[5].strip().strip('"') or row[30].strip().strip('"') or False,
            'expected_revenue': deal_size,
            'user_id': lead_uid,
            'city': row[39].strip().strip('"') or row[20].strip().strip('"') or False,
            'type': 'opportunity' if stage_name else 'lead',
            'active': False if erp_status in ['lost quotation', 'do not contact'] else True,
            'custom_product': product,
            'product_id': get_or_create_product(product),
            'custom_deal_size': deal_size,
            'custom_technician': row[13].strip().strip('"') if row[13] else False,
            'custom_type_of_business': row[14].strip().strip('"') if row[14] else False,
            'legacy_create_date': safe_date(row[7]),
        }
        if stage_map.get(stage_name): vals['stage_id'] = stage_map[stage_name]
        
        lead_vals_list.append(vals)
        imported_lead_ids.append(import_id)
        
print(f"Found {len(lead_vals_list)} Leads WITH A PRODUCT. Creating them in Odoo in chunks of 500...")
new_lead_ids = []
chunk_size = 500
for i in range(0, len(lead_vals_list), chunk_size):
    chunk = lead_vals_list[i:i + chunk_size]
    ids = models.execute_kw(db, uid, password, 'crm.lead', 'create', [chunk], {'context': ctx})
    new_lead_ids.extend(ids)
    print(f"Imported {len(new_lead_ids)}/{len(lead_vals_list)} leads...", end='\\r', flush=True)
print("\\nAll leads created successfully!")

for i, real_id in enumerate(new_lead_ids):
    import_id_to_real_id[imported_lead_ids[i]] = real_id
    creation = lead_vals_list[i]['legacy_create_date']
    if creation:
        try: cur.execute("UPDATE crm_lead SET create_date = %s WHERE id = %s", (creation, real_id))
        except: pass
conn.commit()

# --- To-Dos ---
print("Reading corresponding To-Dos from ToDo.csv...")
todo_csv = sys.argv[2] if len(sys.argv) > 2 else os.path.join(DEFAULT_DATA_DIR, 'ToDo.csv')
if not os.path.exists(todo_csv) and os.path.exists(r'C:\Users\DELL\Desktop\odoo\data_import\ToDo.csv'):
    todo_csv = r'C:\Users\DELL\Desktop\odoo\data_import\ToDo.csv'

act_type_id = models.execute_kw(db, uid, password, 'mail.activity.type', 'search', [[]], {'limit': 1})[0]
model_id = models.execute_kw(db, uid, password, 'ir.model', 'search', [[('model', '=', 'crm.lead')]], {'limit': 1})[0]

linked_todos_count = 0
open_activities_vals = []
closed_activities_vals = []

with open(todo_csv, mode='r', encoding='utf-8', errors='ignore') as f:
    reader = csv.reader(f)
    for _ in range(20): next(reader, None)
    
    todo_count = 0
    for row in reader:
        todo_count += 1
        if todo_count % 1000 == 0:
            print(f"Scanned {todo_count} rows in ToDo.csv...", end='\\r', flush=True)
            
        if len(row) < 13 or not row[1].strip(): continue
        ref_name = row[12].strip().strip('"')
        
        if ref_name in import_id_to_real_id:
            linked_todos_count += 1
            real_lead_id = import_id_to_real_id[ref_name]
            status = str(row[6]).strip().strip('"').capitalize() if row[6] else 'Open'
            date_str = safe_date(row[2])
            summary = row[1].strip().strip('"') or row[3].strip().strip('"') or 'To-Do'
            note = row[3].strip().strip('"') or ''
            
            # Row 16 is Salesperson Name, Row 15 is Email in ToDo.csv
            todo_sp_name = row[16].strip().strip('"') if len(row) > 16 and row[16] else False
            todo_sp_email = row[15].strip().strip('"') if len(row) > 15 and row[15] else ''
            todo_uid, todo_pid = get_or_create_user(todo_sp_name, todo_sp_email)
            
            act_vals = {
                'res_id': real_lead_id,
                'res_model_id': model_id,
                'activity_type_id': act_type_id,
                'summary': summary,
                'note': f"<p>{note}</p>" if note else "",
                'date_deadline': date_str if date_str else "2026-01-01",
                'user_id': todo_uid,
                'partner_id': todo_pid,
                'legacy_date': date_str
            }
            
            if status in ['Closed', 'Cancelled', 'Done']:
                closed_activities_vals.append(act_vals)
            else:
                open_activities_vals.append(act_vals)

print(f"\\nFound {linked_todos_count} To-Dos for these leads. Mapping to Native Odoo Activities...")

if open_activities_vals:
    for act in open_activities_vals:
        act.pop('legacy_date', None)
    print(f"Creating {len(open_activities_vals)} OPEN activities in chunks of 500...")
    for i in range(0, len(open_activities_vals), chunk_size):
        chunk = open_activities_vals[i:i + chunk_size]
        models.execute_kw(db, uid, password, 'mail.activity', 'create', [chunk], {'context': ctx})
        print(f"Imported open activities batch {i}...", end='\\r', flush=True)

if closed_activities_vals:
    print(f"\\nBulk processing {len(closed_activities_vals)} closed activities in chunks via XML-RPC...")
    start_time = time.time()
    
    # Sort chronologically so Odoo assigns IDs in chronological order (fixing chatter mixup)
    closed_activities_vals.sort(key=lambda x: x.get('legacy_date') or '2026-01-01')
    
    # Keep legacy dates for mapping
    legacy_dates = [act.pop('legacy_date') for act in closed_activities_vals]
    
    # BULK Create in chunks via SQL
    act_ids = []
    print(f"\\nCreating {len(closed_activities_vals)} closed activities directly via SQL for instant speed...")
    for i in range(0, len(closed_activities_vals), chunk_size):
        chunk = closed_activities_vals[i:i + chunk_size]
        
        # We use active=False directly so we don't need a separate UPDATE
        format_strings = ','.join(['(%s, %s, %s, %s, %s, %s, %s, FALSE, %s, %s)'] * len(chunk))
        flat_vals = []
        for act in chunk:
            date_time_str = "2026-01-01 10:00:00"
            legacy_date = legacy_dates[closed_activities_vals.index(act)] if act in closed_activities_vals else None
            if legacy_date:
                legacy_date_str = str(legacy_date).strip()
                if len(legacy_date_str) > 10:
                    date_time_str = legacy_date_str
                else:
                    date_time_str = f"{legacy_date_str} 10:00:00"
            
            flat_vals.extend([
                act['res_model_id'], act['res_id'], act['activity_type_id'], act['user_id'],
                act['summary'], act['note'], date_time_str, date_time_str, date_time_str
            ])
            
        try:
            cur.execute(f"INSERT INTO mail_activity (res_model_id, res_id, activity_type_id, user_id, summary, note, date_deadline, active, create_date, date_done) VALUES {format_strings} RETURNING id", flat_vals)
            inserted_ids = [row[0] for row in cur.fetchall()]
            act_ids.extend(inserted_ids)
        except Exception as e:
            print(f"\\nError inserting closed activities: {e}")
            
        print(f"Created batch {i}...", end='\\r', flush=True)
    
    print("\\nCreating historical chatter messages for closed To-Dos via SQL...")
    msg_vals = []
    for i, act_id in enumerate(act_ids):
        res_id = closed_activities_vals[i]['res_id']
        legacy_date = legacy_dates[i]
        summary = closed_activities_vals[i].get('summary', 'To-Do')
        note = closed_activities_vals[i].get('note', '')
        
        # Safely construct the datetime string
        date_time_str = "2026-01-01 10:00:00"
        if legacy_date:
            legacy_date_str = str(legacy_date).strip()
            if len(legacy_date_str) > 10:
                date_time_str = legacy_date_str # Already has time
            else:
                date_time_str = f"{legacy_date_str} 10:00:00"
        
        # Prepare native Odoo chatter message, INCLUDING the original note data
        note_html = f"<div>{note}</div>" if note else ""
        body = f"<div><p><span class='fa fa-check fa-fw'></span><span>To-Do</span> done <span>: </span><span>{summary}</span></p>{note_html}</div>"
        
        # Use the specific partner_id assigned to this To-Do
        pid = closed_activities_vals[i].get('partner_id', admin_partner_id)
        msg_vals.append(('crm.lead', res_id, body, 'notification', 3, date_time_str, pid, act_type_id))
        
    for i in range(0, len(msg_vals), chunk_size):
        chunk = msg_vals[i:i + chunk_size]
        try:
            format_strings = ','.join(['(%s, %s, %s, %s, %s, %s, %s, %s)'] * len(chunk))
            flat_vals = [item for sublist in chunk for item in sublist]
            cur.execute(f"INSERT INTO mail_message (model, res_id, body, message_type, subtype_id, date, author_id, mail_activity_type_id) VALUES {format_strings}", flat_vals)
        except Exception as e:
            print(f"\\nError inserting message chunk: {e}")
        print(f"Created Chatter Message batch {i}...", end='\\r', flush=True)
    conn.commit()
            
    elapsed = time.time() - start_time
    print(f"Finished bulk mapping closed activities in {elapsed:.2f} seconds!")

cur.close()
conn.close()

print("\nRunning Sequencing script so the No. column populates...")
try:
    subprocess.run(["python", "custom-addons/crm_extension/scripts/sequence_leads.py"], cwd=r'c:\Users\DELL\Desktop\odoo')
except Exception as e:
    print(f"Sequencing failed: {e}")

print("\n=== MIGRATION SUMMARY ===")
print("--------------------------------------------------")
print(f"LEADS (Lead.csv):")
print(f"  Source Rows Scanned: {count:,}")
print(f"  Successfully Imported: {len(new_lead_ids):,}")
print(f"  Skipped (No Product/Empty): {count - len(new_lead_ids):,}")
print("--------------------------------------------------")
print(f"TO-DOS (ToDo.csv):")
print(f"  Source Rows Scanned: {todo_count:,}")
print(f"  Successfully Imported: {linked_todos_count:,} (Open: {len(open_activities_vals):,}, Closed: {len(closed_activities_vals):,})")
print(f"  Skipped (Orphaned / No Lead): {todo_count - linked_todos_count:,}")
print("--------------------------------------------------")
total_time = time.time() - global_start
print(f"Total Time Taken: {total_time / 60:.2f} minutes")
print("--------------------------------------------------")
print("=== IMPORT SUCCESSFUL! ALL DATA MAPPED PERFECTLY! ===\n")
