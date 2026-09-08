import os
import csv
import time
import sys

LOG_FILE = '/mnt/extra-addons/havano_crm_extension/import.log'
if not os.path.exists(os.path.dirname(LOG_FILE)):
    LOG_FILE = '/opt/odoo-secure/addons-custom/havano_crm_extension/import.log'

try:
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        f.write('')
except Exception:
        pass

def log(msg):
    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
    formatted = f"[{timestamp}] {msg}"
    print(formatted, flush=True)
    try:
        with open(LOG_FILE, 'a', encoding='utf-8') as f:
            f.write(formatted + '\n')
            f.flush()
    except Exception:
        pass

def safe_commit(database_cr=None):
    try:
        env.cr.commit()
    except Exception:
        pass

log("--- INITIALIZING UNLIMITED LEADS IMPORT (NATIVE ODOO SHELL) ---")
global_start = time.time()

ctx = {'tracking_disable': True, 'mail_create_nolog': True, 'mail_create_nosubscribe': True, 'check_company': False}
env = env(context=ctx)
cr = env.cr

# Fix multi-company restrictions: grant all users access to all companies so no company crossover errors occur!
all_companies = env['res.company'].search([])
all_company_ids = all_companies.ids
main_company_id = env.company.id if env.company else (all_company_ids[0] if all_company_ids else False)

for u in env['res.users'].search([]):
    try:
        u.sudo().write({'company_ids': [(6, 0, all_company_ids)]})
    except Exception:
        pass

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
    try: return float(str(value).replace(',', '').strip('"'))
    except: return 0.0

# Stages
stages = env['crm.stage'].search([])
stage_map = {str(s.name).lower(): s.id for s in stages}

# Products
print("Preloading all products...", flush=True)
products = env['product.product'].search([('default_code', '!=', False)])
product_map = {p.default_code.strip().lower(): p.id for p in products}

admin_partner_id = env.user.partner_id.id

# Preload users
all_users = env['res.users'].search([('name', '!=', False)])
user_map = {str(u.name).lower().strip(): (u.id, u.partner_id.id) for u in all_users}

def get_or_create_user(name, login=''):
    if not name and not login: return env.uid, admin_partner_id
    name = str(name).strip() if name else str(login).strip()
    key = name.lower()
    if key in user_map:
        return user_map[key]
    
    login_val = str(login).strip().lower() if login else f"{name.replace(' ', '').lower()}@example.com"
    
    existing_user = env['res.users'].sudo().search([('login', '=', login_val)], limit=1)
    if existing_user:
        user_map[key] = (existing_user.id, existing_user.partner_id.id)
        return user_map[key]
        
    existing_by_name = env['res.users'].sudo().search([('name', '=ilike', name)], limit=1)
    if existing_by_name:
        user_map[key] = (existing_by_name.id, existing_by_name.partner_id.id)
        return user_map[key]
        
    try:
        new_user = env['res.users'].sudo().create({
            'name': name,
            'login': login_val,
            'company_id': main_company_id,
            'company_ids': [(6, 0, all_company_ids)]
        })
        user_map[key] = (new_user.id, new_user.partner_id.id)
        return user_map[key]
    except Exception:
        return env.uid, admin_partner_id

def get_or_create_product(prod_name):
    if not prod_name: return False
    clean = str(prod_name).strip().strip('"')
    clean_lower = clean.lower()
    
    if clean_lower in product_map: 
        return product_map[clean_lower]
        
    try:
        prod = env['crm.product'].create({'name': clean})
        product_map[clean_lower] = prod.id
        return prod.id
    except Exception:
        return False

# Data import paths inside container mount
lead_csv = '/mnt/extra-addons/havano_crm_extension/data_import/Lead.csv'
todo_csv = '/mnt/extra-addons/havano_crm_extension/data_import/ToDo.csv'

if not os.path.exists(lead_csv):
    lead_csv = '/opt/odoo-secure/addons-custom/havano_crm_extension/data_import/Lead.csv'
if not os.path.exists(todo_csv):
    todo_csv = '/opt/odoo-secure/addons-custom/havano_crm_extension/data_import/ToDo.csv'

# Preload existing leads to prevent duplicates (match strictly on legacy ID / custom_naming_series)
print("Preloading existing leads in Odoo (including active and archived)...", flush=True)
cr.execute("SELECT id, custom_naming_series FROM crm_lead WHERE custom_naming_series IS NOT NULL;")
existing_leads_map = {str(row[1]).strip(): row[0] for row in cr.fetchall() if row[1]}
print(f"Preloaded {len(existing_leads_map):,} existing leads from database. Duplicates will be strictly skipped.", flush=True)

lead_vals_list = []
imported_lead_ids = []
import_id_to_real_id = {}

print(f"Reading ALL Leads from {lead_csv}...", flush=True)
with open(lead_csv, mode='r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    
    count = 0
    for r in reader:
        count += 1
        if count % 2000 == 0:
            print(f"Scanned {count:,} rows in Lead.csv...", flush=True)
            
        import_id = (r.get('ID') or '').strip().strip('"')
        if not import_id or import_id in imported_lead_ids:
            continue
            
        product = (r.get('Product') or '').strip().strip('"') or False
        erp_status = (r.get('Status') or '').strip().strip('"').lower()
        company = (r.get('Organization/Store  Name') or '').strip().strip('"') or False
        contact = (r.get('First Name') or r.get('Full Name') or '').strip().strip('"') or False
        deal_size = safe_float(r.get('Deal Size $')) or safe_float(r.get('Deal size'))
        
        # Build unique descriptive lead name (Company/Contact + Product)
        if company and product:
            name_val = f"{company} - {product}"
        elif contact and product:
            name_val = f"{contact} - {product}"
        elif company:
            name_val = company
        elif contact:
            name_val = contact
        elif product:
            name_val = f"{import_id} - {product}"
        else:
            name_val = import_id
        
        salesperson_name = (r.get('Lead Owner') or '').strip().strip('"') or False
        lead_uid, lead_pid = get_or_create_user(salesperson_name)
        
        stage_name = 'qualified' if erp_status in ['lead', 'open', 'interested', 'replied', 'opportunity', 'quotation'] else 'won' if erp_status == 'converted' else None
        
        # Additional fields
        technician = (r.get('Technician') or '').strip().strip('"') or False
        biz_type = (r.get('Type of Business') or '').strip().strip('"') or False
        quote_val = (r.get('Quote') or '').strip().strip('"')
        quote_status = 'Quote' if quote_val and 'quote' in quote_val.lower() and 'not' not in quote_val.lower() else ('Not yet Quoted' if quote_val else False)
        quote_date = safe_date(r.get('Quote Date'))
        
        demo_done_str = (r.get('Demo Done ') or '').strip().strip('"').lower()
        demo_done = True if demo_done_str and demo_done_str not in ['no', 'no demo', '0', 'false'] else False
        demo_type = (r.get('Demo Done Online or Onsite') or '').strip().strip('"') or False
        if demo_type and demo_type not in ['Online', 'Onsite']:
            demo_type = 'N/A' if demo_done else False
            
        proposal_val = (r.get('Proposal') or '').strip().strip('"').capitalize()
        proposal_status = proposal_val if proposal_val in ['Not Yet', 'Proposed', 'Accepted', 'Rejected'] else False
        proposal_date = safe_date(r.get('Proposal Date'))
        
        phone_val = (r.get('Mobile No') or r.get('Phone') or r.get('WhatsApp') or '').strip().strip('"') or False
        email_val = (r.get('Email') or r.get('email_id') or '').strip().strip('"') or False
        city_val = (r.get('City /Town') or r.get('City') or '').strip().strip('"') or False
        street_val = (r.get('Full Address') or '').strip().strip('"') or False
        creation_date = safe_date(r.get('Qualified on')) or safe_date(r.get('Added On (Notes)')) or safe_date(r.get('creation'))
        
        vals = {
            'custom_naming_series': import_id,
            'name': name_val,
            'contact_name': contact,
            'partner_name': company,
            'company_id': main_company_id,
            'email_from': email_val,
            'phone': phone_val,
            'expected_revenue': deal_size,
            'user_id': lead_uid,
            'city': city_val,
            'street': street_val,
            'type': 'opportunity',
            'active': True,
            'custom_product': product if product else False,
            'custom_deal_size': deal_size,
            'custom_technician': technician,
            'custom_type_of_business': biz_type,
            'custom_quote': quote_status,
            'custom_quote_date': quote_date,
            'custom_demo_done': demo_done,
            'custom_demo_type': demo_type,
            'custom_proposal_status': proposal_status,
            'custom_proposal_date': proposal_date,
            'legacy_create_date': creation_date,
        }
        if stage_map.get(stage_name): vals['stage_id'] = stage_map[stage_name]
        
        prod_id = get_or_create_product(product)
        if prod_id: vals['product_id'] = prod_id
        
        # Check if already exists in Odoo by legacy ID
        existing_id = existing_leads_map.get(import_id)
        if existing_id:
            import_id_to_real_id[import_id] = existing_id
            continue

        lead_vals_list.append(vals)
        imported_lead_ids.append(import_id)

total_leads = len(lead_vals_list)
print(f"Found {total_leads:,} Leads to process. Creating in Odoo in chunks of 200...", flush=True)

chunk_size = 200
new_leads = []
lead_create_start = time.time()

for i in range(0, total_leads, chunk_size):
    chunk = lead_vals_list[i:i + chunk_size]
    try:
        created = env['crm.lead'].sudo().with_context(ctx).create(chunk)
        new_leads.extend(created)
        env.cr.commit()
    except Exception as e:
        print(f"Warning creating batch {i}: {e}. Creating items individually...", flush=True)
        for single_vals in chunk:
            try:
                single_created = env['crm.lead'].sudo().with_context(ctx).create(single_vals)
                new_leads.extend(single_created)
            except Exception as single_e:
                print(f"Skipped lead '{single_vals.get('name')}': {single_e}", flush=True)
        env.cr.commit()
        
    done = len(new_leads)
    pct = (done / total_leads * 100) if total_leads > 0 else 100.0
    elapsed = time.time() - lead_create_start
    avg_per_item = elapsed / done if done > 0 else 0
    rem_items = total_leads - done
    eta_mins = (rem_items * avg_per_item) / 60.0
    
    print(f"Leads Creation Progress: {done:,}/{total_leads:,} ({pct:.1f}%) | Speed: {done/elapsed:.1f} leads/sec | ETA: {eta_mins:.1f} min", flush=True)

for lead_rec in new_leads:
    if hasattr(lead_rec, 'custom_naming_series') and lead_rec.custom_naming_series:
        series_clean = lead_rec.custom_naming_series.strip()
        import_id_to_real_id[series_clean] = lead_rec.id
        existing_leads_map[series_clean] = lead_rec.id
    if hasattr(lead_rec, 'legacy_create_date') and lead_rec.legacy_create_date:
        try: cr.execute("UPDATE crm_lead SET create_date = %s WHERE id = %s", (lead_rec.legacy_create_date, lead_rec.id))
        except Exception: pass
env.cr.commit()
print(f"Registered {len(new_leads):,} newly created leads into ID map and updated creation dates.", flush=True)

# --- To-Dos ---
print(f"Reading corresponding To-Dos from {todo_csv}...", flush=True)
act_type = env['mail.activity.type'].sudo().search([], limit=1)
act_type_id = act_type.id if act_type else 1
if not act_type_id:
    cr.execute("SELECT id FROM mail_activity_type LIMIT 1;")
    row = cr.fetchone()
    if row: act_type_id = row[0]

model_rec = env['ir.model'].sudo().search([('model', '=', 'crm.lead')], limit=1)
crm_lead_model_id = model_rec.id if model_rec else False
if not crm_lead_model_id:
    cr.execute("SELECT id FROM ir_model WHERE model = 'crm.lead' LIMIT 1;")
    row = cr.fetchone()
    if row: crm_lead_model_id = row[0]

# Preload existing open activities and chatter notes to guarantee ZERO duplicates
print("Preloading existing open activities and chatter notes from Odoo...", flush=True)
cr.execute("SELECT res_id, summary FROM mail_activity WHERE res_model = 'crm.lead' AND summary IS NOT NULL;")
existing_open_activities = set((r[0], str(r[1]).strip()) for r in cr.fetchall())

cr.execute("SELECT res_id, body FROM mail_message WHERE model = 'crm.lead';")
existing_chatter_notes = set((r[0], str(r[1]).strip()) for r in cr.fetchall() if r[1])

linked_todos_count = 0
open_activities_vals = []
closed_activities_vals = []

with open(todo_csv, mode='r', encoding='utf-8', errors='ignore') as f:
    reader = csv.DictReader(f)
    
    todo_count = 0
    for row in reader:
        todo_count += 1
        if todo_count % 5000 == 0:
            print(f"Scanned {todo_count:,} rows in ToDo.csv...", flush=True)
            
        ref_name = (row.get('Reference Name') or '').strip().strip('"')
        if not ref_name: continue
        
        if ref_name in import_id_to_real_id:
            real_lead_id = import_id_to_real_id[ref_name]
            status = (row.get('Status') or 'Open').strip().strip('"').capitalize()
            date_str = safe_date(row.get('Due Date'))
            raw_note = (row.get('Description') or '').strip().strip('"')
            
            # Clean HTML to extract actual readable chatter / note text
            clean_text = ''
            if raw_note:
                import html as html_lib, re as re_lib
                clean_text = html_lib.unescape(re_lib.sub(r'<[^>]+>', ' ', raw_note)).strip()
                clean_text = re_lib.sub(r'\s+', ' ', clean_text).strip()

            summary = clean_text[:200] if clean_text else 'To-Do'
            note = raw_note or ''
            
            todo_sp_name = (row.get('Assigned By Full Name') or '').strip().strip('"') or False
            todo_sp_email = (row.get('Assigned By') or '').strip().strip('"') or ''
            todo_uid, todo_pid = get_or_create_user(todo_sp_name, todo_sp_email)
            
            act_vals = {
                'res_model': 'crm.lead',
                'res_model_id': crm_lead_model_id,
                'res_id': real_lead_id,
                'activity_type_id': act_type_id,
                'summary': summary,
                'note': f"<p>{note}</p>" if note else "",
                'date_deadline': date_str if date_str else "2026-01-01",
                'user_id': todo_uid,
                'legacy_date': date_str,
                'chatter_pid': todo_pid
            }
            
            if status in ['Closed', 'Cancelled', 'Done']:
                note_html = f"<div>{note}</div>" if note else ""
                body = f"<div><p><span class='fa fa-check fa-fw'></span><span>To-Do</span> done <span>: </span><span>{summary}</span></p>{note_html}</div>"
                if (real_lead_id, body) in existing_chatter_notes:
                    continue
                existing_chatter_notes.add((real_lead_id, body))
                closed_activities_vals.append(act_vals)
                linked_todos_count += 1
            else:
                if (real_lead_id, summary) in existing_open_activities:
                    continue
                existing_open_activities.add((real_lead_id, summary))
                open_activities_vals.append(act_vals)
                linked_todos_count += 1

total_open = len(open_activities_vals)
if total_open > 0:
    print(f"Creating {total_open:,} OPEN activities via Odoo ORM...", flush=True)
    open_start = time.time()
    chunk_size = 500
    for i in range(0, total_open, chunk_size):
        chunk = open_activities_vals[i:i + chunk_size]
        orm_chunk = []
        for act in chunk:
            date_deadline = act.get('date_deadline') or '2026-01-01'
            if len(str(date_deadline)) > 10:
                date_deadline = str(date_deadline)[:10]
            orm_chunk.append({
                'res_model': 'crm.lead',
                'res_model_id': act['res_model_id'],
                'res_id': act['res_id'],
                'activity_type_id': act['activity_type_id'],
                'user_id': act['user_id'],
                'summary': act['summary'],
                'note': act['note'],
                'date_deadline': date_deadline,
            })
        try:
            env['mail.activity'].sudo().create(orm_chunk)
            env.cr.commit()
        except Exception as e:
            try: env.cr.rollback()
            except Exception: pass
            print(f"Warning: batch open activities ORM insert failed ({e}). Inserting items individually...", flush=True)
            for act_dict in orm_chunk:
                try:
                    env['mail.activity'].sudo().create(act_dict)
                    env.cr.commit()
                except Exception as single_e:
                    try: env.cr.rollback()
                    except Exception: pass
                    print(f"Skipped 1 open activity: {single_e}", flush=True)
        
        done = min(i + chunk_size, total_open)
        pct = (done / total_open * 100)
        elapsed = time.time() - open_start
        eta_mins = ((total_open - done) * (elapsed / done)) / 60.0 if done > 0 else 0
        print(f"Open Activities Progress: {done:,}/{total_open:,} ({pct:.1f}%) | ETA: {eta_mins:.1f} min", flush=True)

total_closed = len(closed_activities_vals)
if total_closed > 0:
    print(f"Processing {total_closed:,} CLOSED activities into Chatter...", flush=True)
    closed_activities_vals.sort(key=lambda x: x.get('legacy_date') or '2026-01-01')
    
    msg_vals = []
    for act in closed_activities_vals:
        res_id = act['res_id']
        legacy_date = act.get('legacy_date')
        summary = act.get('summary', 'To-Do')
        note = act.get('note', '')
        date_time_str = "2026-01-01 10:00:00"
        if legacy_date:
            legacy_date_str = str(legacy_date).strip()
            date_time_str = legacy_date_str if len(legacy_date_str) > 10 else f"{legacy_date_str} 10:00:00"
        note_html = f"<div>{note}</div>" if note else ""
        body = f"<div><p><span class='fa fa-check fa-fw'></span><span>To-Do</span> done <span>: </span><span>{summary}</span></p>{note_html}</div>"
        pid = act.get('chatter_pid', admin_partner_id)
        msg_vals.append(('crm.lead', res_id, body, 'notification', 3, date_time_str, pid, act_type_id))
        
    if msg_vals:
        total_msgs = len(msg_vals)
        msg_start = time.time()
        chunk_size = 500
        for i in range(0, total_msgs, chunk_size):
            chunk = msg_vals[i:i + chunk_size]
            format_strings = ','.join(['(%s, %s, %s, %s, %s, %s, %s, %s)'] * len(chunk))
            flat_vals = [item for sublist in chunk for item in sublist]
            try:
                cr.execute(f"INSERT INTO mail_message (model, res_id, body, message_type, subtype_id, date, author_id, mail_activity_type_id) VALUES {format_strings}", flat_vals)
                env.cr.commit()
            except Exception as e:
                try: env.cr.rollback()
                except Exception: pass
                print(f"Warning: chatter messages batch failed ({e}). Inserting items individually...", flush=True)
                for item in chunk:
                    try:
                        cr.execute("INSERT INTO mail_message (model, res_id, body, message_type, subtype_id, date, author_id, mail_activity_type_id) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", item)
                        env.cr.commit()
                    except Exception as single_e:
                        try: env.cr.rollback()
                        except Exception: pass
                        print(f"Skipped 1 chatter message: {single_e}", flush=True)
            done = min(i + chunk_size, total_msgs)
            pct = (done / total_msgs * 100)
            elapsed = time.time() - msg_start
            eta_mins = ((total_msgs - done) * (elapsed / done)) / 60.0 if done > 0 else 0
            print(f"Chatter Messages Progress: {done:,}/{total_msgs:,} ({pct:.1f}%) | ETA: {eta_mins:.1f} min", flush=True)
        env.cr.commit()

# Apply sequence numbers
print("Sequencing leads (custom_no column)...", flush=True)
try:
    cr.execute("ALTER TABLE crm_lead ADD COLUMN IF NOT EXISTS custom_no integer;")
    cr.execute("SELECT id FROM crm_lead ORDER BY COALESCE(legacy_create_date, create_date) ASC, id ASC;")
    leads = cr.fetchall()
    counter = 1
    for lead_id, in leads:
        cr.execute("UPDATE crm_lead SET custom_no = %s WHERE id = %s", (counter, lead_id))
        counter += 1
    safe_commit(cr)
    print(f"Sequenced {len(leads):,} leads.", flush=True)
except Exception as seq_err:
    try: cr.rollback()
    except Exception: pass
    print(f"Sequencing warning (skipped): {seq_err}", flush=True)

# Update any existing mail_activity records so their summary displays actual readable chatter note instead of legacy IDs
print("Updating mail_activity summaries to show actual chatter note text...", flush=True)
import html as html_lib, re as re_lib
cr.execute("SELECT id, summary, note FROM mail_activity WHERE res_model = 'crm.lead' AND note IS NOT NULL AND TRIM(note) != '';")
acts_to_fix = cr.fetchall()
fixed_acts = 0
for act_id, act_sum, act_note in acts_to_fix:
    if act_note:
        c_text = html_lib.unescape(re_lib.sub(r'<[^>]+>', ' ', act_note)).strip()
        c_text = re_lib.sub(r'\s+', ' ', c_text).strip()
        if c_text:
            cr.execute("UPDATE mail_activity SET summary = %s WHERE id = %s", (c_text[:200], act_id))
            fixed_acts += 1
safe_commit(cr)
print(f"Updated {fixed_acts:,} mail_activity summaries with actual chatter notes.", flush=True)

# Update existing mail_message bodies for closed To-Dos
print("Updating closed To-Do chatter messages...", flush=True)
cr.execute("SELECT id, body FROM mail_message WHERE model = 'crm.lead' AND body LIKE '%<span>To-Do</span> done%';")
msgs_to_fix = cr.fetchall()
fixed_msgs = 0
for msg_id, body_html in msgs_to_fix:
    if body_html and '<span>To-Do</span> done' in body_html:
        # Extract note text from inner divs
        inner_matches = re_lib.findall(r'<div>(.*?)</div>', body_html, re_lib.DOTALL)
        if len(inner_matches) > 1:
            desc_html = inner_matches[-1]
            c_text = html_lib.unescape(re_lib.sub(r'<[^>]+>', ' ', desc_html)).strip()
            c_text = re_lib.sub(r'\s+', ' ', c_text).strip()
            if c_text:
                new_body = re_lib.sub(r'(<span>To-Do</span> done <span>: </span><span>)[^<]*(</span>)', r'\g<1>' + html_lib.escape(c_text[:200]) + r'\2', body_html)
                cr.execute("UPDATE mail_message SET body = %s WHERE id = %s", (new_body, msg_id))
                fixed_msgs += 1
safe_commit(cr)
print(f"Updated {fixed_msgs:,} chatter messages.", flush=True)

print("Recomputing Last Chatter & Last To-Do / Note column across all leads...", flush=True)
try:
    all_leads = env['crm.lead'].with_context(active_test=False).search([])
    all_leads._compute_last_chatter()
    all_leads._compute_last_todo_note()
    safe_commit(cr)
except Exception as e:
    print(f"Note recompute warning: {e}", flush=True)

total_time = time.time() - global_start
print("--------------------------------------------------", flush=True)
print(f"=== MIGRATION COMPLETE SUCCESSFULLY IN {total_time / 60:.2f} MINUTES ===", flush=True)
print("--------------------------------------------------", flush=True)
#sudo bash /opt/odoo-secure/addons-custom/havano_crm_extension/run_import.sh
#sudo python3 /opt/odoo-secure/addons-custom/havano_crm_extension/scripts/clean_duplicate_activities.py

