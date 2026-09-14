from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64
import io
import logging
import re
import html

_logger = logging.getLogger(__name__)

try:
    import openpyxl
except ImportError:
    openpyxl = None

def _safe_str(val, default=''):
    if val is None:
        return default
    s = str(val).strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    return s if s and s.lower() != 'none' else default

def _clean_html(val):
    if not val:
        return ''
    s = html.unescape(str(val))
    s = re.sub(r'<[^>]+>', ' ', s).strip()
    s = re.sub(r'\s+', ' ', s).strip()
    return s

def _clean_datetime(val):
    if val is None: return False
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d %H:%M:%S')
    s = str(val).strip().replace('T', ' ')
    if not s or s.lower() == 'none': return False
    if '.' in s: s = s[:s.index('.')]
    if len(s) == 10: s += ' 00:00:00'
    return s if len(s) >= 10 else False

def _is_phone(val):
    if not val:
        return False
    cleaned = re.sub(r'[\s\+\-\(\)\.]', '', str(val).strip())
    return bool(cleaned and cleaned.isdigit() and len(cleaned) >= 7)

def _extract_lead_names_and_contact(r):
    # Support multiple variations of CSV column headers
    first_name = _safe_str(r.get('First Name') or r.get('first_name') or r.get('lead_name') or r.get('Lead Name'))
    last_name = _safe_str(r.get('Last Name') or r.get('last_name'))
    full_name = _safe_str(r.get('Full Name') or r.get('full_name') or r.get('contact_name') or r.get('Contact Name'))
    
    org_name = _safe_str(
        r.get('Organization/Store  Name') or 
        r.get('Organization/Store Name') or 
        r.get('company_name') or 
        r.get('Company Name') or 
        r.get('Company') or 
        r.get('company')
    )
    if org_name.lower() in ['showline solutions', 'maypack solutions', 'showline', 'maypack']:
        org_name = ''

    mobile_no = _safe_str(r.get('Mobile No') or r.get('mobile_no') or r.get('Phone') or r.get('phone') or r.get('WhatsApp') or r.get('whatsapp'))
    email_val = _safe_str(r.get('Email') or r.get('email_id') or r.get('email'))

    # If first_name or full_name is actually a phone number, reassign to mobile_no and clear name
    if first_name and _is_phone(first_name):
        if not mobile_no:
            mobile_no = first_name
        first_name = ''
        
    if full_name and _is_phone(full_name):
        if not mobile_no:
            mobile_no = full_name
        full_name = ''

    # 1. Build human contact name
    contact_name = ''
    if full_name:
        contact_name = full_name
    elif first_name or last_name:
        contact_name = " ".join([p for p in [first_name, last_name] if p]).strip()
        
    # 2. If contact name is still empty, fallback to Organization/Store Name
    if not contact_name and org_name:
        contact_name = org_name
        
    # 3. If still empty, fallback to clean email prefix (e.g. john.doe@... -> John Doe)
    if not contact_name and email_val and '@' in email_val:
        prefix = email_val.split('@')[0]
        clean_p = re.sub(r'[\._\-0-9]+', ' ', prefix).strip().title()
        if clean_p and len(clean_p) >= 3 and not clean_p.isdigit():
            contact_name = clean_p

    # 4. If still empty, fallback to "Contact <Phone>" or "Lead <ID>"
    if not contact_name:
        if mobile_no:
            contact_name = f"Contact {mobile_no}"
        else:
            legacy_id = _safe_str(r.get('name') or r.get('id') or r.get('ID'))
            contact_name = f"Lead {legacy_id}" if legacy_id else "New Lead"

    return contact_name, org_name, mobile_no, email_val

def _clean_date(val):
    if val is None: return False
    if hasattr(val, 'strftime'): return val.strftime('%Y-%m-%d')
    s = str(val).strip()
    if not s or s.lower() == 'none': return False
    if ' ' in s: s = s.split(' ')[0]
    parts = re.split(r'[-/]', s)
    if len(parts) == 3:
        p1, p2, p3 = parts[0], parts[1], parts[2]
        if len(p1) == 4: return f"{p1}-{p2.zfill(2)}-{p3.zfill(2)}"
        elif len(p3) == 4: return f"{p3}-{p2.zfill(2)}-{p1.zfill(2)}"
    return False

def _parse_csv_or_excel(file_bytes, filename):
    import csv
    rows = []
    if filename and filename.lower().endswith('.csv'):
        content = file_bytes.decode('utf-8', errors='ignore')
        reader = csv.reader(io.StringIO(content))
        rows = list(reader)
    else:
        wb = openpyxl.load_workbook(filename=io.BytesIO(file_bytes), data_only=True, read_only=True)
        ws = wb.active
        rows = list(ws.iter_rows(values_only=True))
        wb.close()

    if not rows:
        return []

    headers = None
    data_start_row = 0
    is_erpnext_template = False

    for i, row in enumerate(rows):
        first_col = str(row[0]).strip() if row and row[0] else ""
        if first_col == "Column Name:":
            headers = [str(c).strip() if c is not None else "" for c in row[1:]]
            data_start_row = i + 5
            is_erpnext_template = True
            break
            
    if not is_erpnext_template:
        headers = [str(c).strip() if c is not None else "" for c in rows[0]]
        data_start_row = 1

    records = []
    col_offset = 1 if is_erpnext_template else 0
    
    for row in rows[data_start_row:]:
        if not any(row):
            continue
        row_dict = {}
        for idx, h in enumerate(headers):
            if h == '~':
                break
            if h and h not in row_dict:
                data_col = idx + col_offset
                row_dict[h] = row[data_col] if data_col < len(row) else None
        records.append(row_dict)
        
    return records

class CrmImportWizard(models.TransientModel):
    _name = 'crm.import.wizard'
    _description = 'Data Import Wizard'

    import_type = fields.Selection([
        ('user', '1. Users'),
        ('source', '2. Lead Sources'),
        ('lead', '3. Leads'),
        ('todo', '4. To-Dos'),
    ], string='What are you importing?', required=True, default='lead')

    data_file = fields.Binary(string='File (CSV/Excel)', required=True)
    filename = fields.Char(string='Filename')

    def action_import_data(self):
        if not self.data_file:
            raise UserError(_("Please upload a file."))
        
        file_bytes = base64.b64decode(self.data_file)
        records = _parse_csv_or_excel(file_bytes, self.filename)

        if not records:
            raise UserError(_("No valid data rows found."))

        created = 0
        updated = 0
        skipped = 0

        if self.import_type == 'user':
            existing_emails = set(self.env['res.users'].sudo().with_context(active_test=False).search([]).mapped('login'))
            existing_names = set(p.lower() for p in self.env['res.partner'].sudo().with_context(active_test=False).search([]).mapped('name') if p)
            users_to_create = []
            
            for r in records:
                # Support various column names
                email = _safe_str(r.get('email') or r.get('email_id') or r.get('owner'))
                name = _safe_str(r.get('full_name') or r.get('first_name') or email)
                
                if not email or email in existing_emails or name.lower() in existing_names:
                    skipped += 1
                    continue
                
                existing_emails.add(email) # Prevent duplicates in same file
                existing_names.add(name.lower())
                users_to_create.append({
                    'name': name or email,
                    'login': email,
                    'email': email,
                    'password': 'ImportedUser@2024',
                })
                
            if users_to_create:
                for u_vals in users_to_create:
                    try:
                        with self.env.cr.savepoint():
                            self.env['res.users'].sudo().with_context(no_reset_password=True, mail_create_nolog=True, mail_notrack=True, check_duplicate=False).create([u_vals])
                            self.env.flush_all()
                        created += 1
                    except Exception as e:
                        _logger.warning("Failed to create user %s: %s", u_vals.get('login'), str(e))
                        skipped += 1

        elif self.import_type == 'source':
            cr = self.env.cr
            cr.execute("SELECT lower(name), id FROM utm_source")
            existing_sources = {r[0]: r[1] for r in cr.fetchall() if r[0]}
            sources_to_create = []
            
            for r in records:
                src_name = _safe_str(r.get('source_name') or r.get('name') or r.get('source'))
                if not src_name or src_name.lower() in existing_sources:
                    skipped += 1
                    continue
                
                existing_sources[src_name.lower()] = True
                sources_to_create.append({'name': src_name})
            
            if sources_to_create:
                self.env['utm.source'].sudo().create(sources_to_create)
                created = len(sources_to_create)

        elif self.import_type == 'lead':
            first_rec = records[0] if records else {}
            if 'reference_name' in first_rec and 'reference_type' in first_rec and 'lead_name' not in first_rec:
                raise UserError(_("The uploaded file appears to be a To-Dos file (ToDo.csv), but you selected '3. Leads'. Please select '4. To-Dos'."))

            cr = self.env.cr
            # Fast fetch existing lead IDs directly from DB
            cr.execute("SELECT custom_naming_series FROM crm_lead WHERE custom_naming_series IS NOT NULL")
            existing_leads = set(r[0] for r in cr.fetchall() if r[0])
            
            # Pre-fetch users for fast mapping with aliases and domain cleanups
            cr.execute("""
                SELECT u.id, u.login, p.email, p.name 
                FROM res_users u 
                LEFT JOIN res_partner p ON u.partner_id = p.id 
                WHERE u.active IS TRUE
                ORDER BY 
                    CASE WHEN u.login LIKE '%@example.com' THEN 0 ELSE 1 END ASC,
                    CASE WHEN p.name LIKE '%@%' THEN 0 ELSE 1 END ASC,
                    u.id ASC
            """)
            user_map = {}
            for r in cr.fetchall():
                uid_val, login, email, pname = r[0], (r[1] or '').strip().lower(), (r[2] or '').strip().lower(), (r[3] or '').strip().lower()
                if login:
                    user_map[login] = uid_val
                    if login.endswith('@example.com'):
                        user_map[login.replace('@example.com', '')] = uid_val
                if email and email != 'false':
                    user_map[email] = uid_val
                if pname:
                    user_map[pname] = uid_val
            user_map['administrator'] = 2
            user_map['admin'] = 2

            # Pre-fetch sources for fast mapping
            cr.execute("SELECT lower(name), id FROM utm_source WHERE name IS NOT NULL")
            source_map = {r[0]: r[1] for r in cr.fetchall() if r[0]}
            
            crm_lead_fields = self.env['crm.lead']._fields
            has_crm_product_field = 'crm_product_id' in crm_lead_fields
            has_crm_product_model = 'crm.product' in self.env

            leads_to_create = []
            leads_to_update = []
            updated = 0

            for r in records:
                legacy_id = _safe_str(r.get('name') or r.get('id') or r.get('ID'))
                if not legacy_id:
                    skipped += 1
                    continue
                
                contact_name, company_name, mobile_no, email_val = _extract_lead_names_and_contact(r)
                territory = _safe_str(r.get('territory') or r.get('Territory'))
                product = _safe_str(r.get('custom_product') or r.get('Product'))

                # Look up or create in standalone crm.product
                crm_product_id = False
                if product:
                    try:
                        crm_prod = self.env['crm.product'].sudo().search([('name', '=ilike', product)], limit=1)
                        if crm_prod:
                            crm_product_id = crm_prod.id
                        else:
                            crm_product_id = self.env['crm.product'].sudo().create({'name': product}).id
                    except Exception:
                        pass

                status_val = _safe_str(r.get('status') or r.get('Status'))
                stage_id = 1
                probability = 10.0
                active = True
                
                if status_val == 'Converted':
                    stage_id = 4
                    probability = 100.0
                elif status_val in ['Quotation', 'Opportunity']:
                    stage_id = 3
                    probability = 80.0
                elif status_val in ['Interested', 'Replied']:
                    stage_id = 2
                    probability = 50.0
                elif status_val in ['Do Not Contact', 'Lost Quotation']:
                    active = False
                    probability = 0.0

                creator_raw = _safe_str(r.get('owner') or r.get('Created By') or r.get('created_by'))
                create_uid_val = user_map.get(creator_raw.lower()) if creator_raw else False

                salesperson_raw = _safe_str(r.get('lead_owner') or r.get('Lead Owner') or r.get('salesperson') or r.get('owner'))
                user_id = user_map.get(salesperson_raw.lower()) if salesperson_raw else create_uid_val

                creation_date = _clean_datetime(r.get('creation') or r.get('Creation') or r.get('Added On (Notes)'))
                
                deal_size = 0.0
                try: deal_size = float(r.get('custom_deal_size_') or r.get('Deal Size $') or r.get('Deal size') or 0)
                except: pass

                raw_src = _safe_str(r.get('source') or r.get('Source'))
                source_id = False
                if raw_src:
                    if raw_src.lower() in source_map:
                        source_id = source_map[raw_src.lower()]
                    else:
                        new_src = self.env['utm.source'].sudo().create({'name': raw_src})
                        source_id = new_src.id
                        source_map[raw_src.lower()] = source_id

                street_val = _safe_str(r.get('custom_full_address') or r.get('Full Address') or r.get('street'))
                city_val = _safe_str(r.get('custom_city_town') or r.get('City /Town') or r.get('city') or r.get('City'))
                notes_val = _safe_str(r.get('custom_detailed_info') or r.get('Detailed Info') or r.get('Note (Notes)') or r.get('note') or r.get('description'))
                if notes_val:
                    if not ('<' in notes_val and '>' in notes_val):
                        notes_val = f"<p>{html.escape(notes_val).replace(chr(10), '<br/>')}</p>"

                demo_raw = str(r.get('custom_demo_done_') or r.get('Demo Done ') or r.get('custom_demo_done') or '').strip().lower()
                demo_done = 'yes' if 'demo' in demo_raw and 'no' not in demo_raw else ('yes' if demo_raw == 'yes' else 'no')
                
                demo_type_raw = str(r.get('custom_demo_done_online_or_onsite') or r.get('Demo Done Online or Onsite') or r.get('custom_demo_type') or '').strip()
                demo_type = 'Onsite' if 'onsite' in demo_type_raw.lower() else ('Online' if 'online' in demo_type_raw.lower() else 'N/A')

                if legacy_id in existing_leads:
                    # Queue for prepopulating existing leads across all fields if missing in DB
                    leads_to_update.append((
                        legacy_id,
                        contact_name or None,
                        company_name or None,
                        mobile_no or None,
                        email_val or None,
                        crm_product_id or None,
                        product or None,
                        source_id or None,
                        raw_src or None,
                        territory or None,
                        _safe_str(r.get('industry') or r.get('Industry')) or None,
                        street_val or None,
                        city_val or None,
                        notes_val or None,
                        deal_size if deal_size > 0 else 0.0,
                        _safe_str(r.get('custom_type_of_business') or r.get('Type of Business')) or None,
                        demo_done or 'no',
                        demo_type or 'N/A',
                        _clean_date(r.get('custom_quote_date') or r.get('Quote Date')) or None,
                        _safe_str(r.get('custom_technician') or r.get('Technician')) or None,
                        user_id or None,
                        create_uid_val or None,
                        creation_date or None
                    ))
                    continue
                
                existing_leads.add(legacy_id)
                
                parts = []
                if contact_name: parts.append(contact_name)
                if company_name and company_name != contact_name: parts.append(company_name)
                if territory: parts.append(territory)
                
                title = " - ".join(parts).strip()
                if product:
                    title = f"{title} - {product}" if title else product
                if not title:
                    title = contact_name or "Unknown Lead"

                lead_vals = {
                    'name': title,
                    'contact_name': contact_name,
                    'partner_name': company_name or False,
                    'phone': mobile_no or False,
                    'email_from': email_val or False,
                    'custom_naming_series': legacy_id,
                    'source_id': source_id,
                    'custom_lead_source': raw_src or False,
                    'custom_territory': _safe_str(r.get('territory') or r.get('Territory')),
                    'custom_industry': _safe_str(r.get('industry') or r.get('Industry')),
                    'custom_product': product or False,
                    'street': street_val or False,
                    'city': city_val or False,
                    'description': notes_val or False,
                    'expected_revenue': deal_size,
                    'custom_deal_size': deal_size,
                    'custom_type_of_business': _safe_str(r.get('custom_type_of_business') or r.get('Type of Business')),
                    'custom_demo_done': demo_done,
                    'custom_demo_type': demo_type,
                    'custom_quote_date': _clean_date(r.get('custom_quote_date') or r.get('Quote Date')),
                    'custom_technician': _safe_str(r.get('custom_technician') or r.get('Technician')),
                    'user_id': user_id,
                    'stage_id': stage_id,
                    'probability': probability,
                    'active': active,
                    'create_date': creation_date,
                    'legacy_create_date': creation_date,
                    '_create_uid': create_uid_val,
                }
                if has_crm_product_field and crm_product_id:
                    lead_vals['crm_product_id'] = crm_product_id
                leads_to_create.append(lead_vals)
            
            if leads_to_create:
                for i in range(0, len(leads_to_create), 500):
                    batch = leads_to_create[i:i+500]
                    orm_batch = []
                    for b in batch:
                        b_copy = dict(b)
                        b_copy.pop('_create_uid', None)
                        orm_batch.append(b_copy)
                        
                    created_recs = self.env['crm.lead'].sudo().with_context(
                        mail_create_nolog=True,
                        mail_create_nosubscribe=True,
                        tracking_disable=True,
                        prefetch_fields=False
                    ).create(orm_batch)
                    for idx, rec in enumerate(created_recs):
                        c_uid = batch[idx].get('_create_uid')
                        leg_date = rec.legacy_create_date
                        if c_uid or leg_date:
                            self.env.cr.execute("""
                                UPDATE crm_lead 
                                SET create_date = COALESCE(%s, create_date),
                                    create_uid = COALESCE(%s, create_uid)
                                WHERE id = %s
                            """, (leg_date, c_uid, rec.id))
                    created += len(batch)

            if leads_to_update:
                from psycopg2.extras import execute_values
                self.env.cr.execute("""
                    CREATE TEMP TABLE IF NOT EXISTS tmp_lead_update (
                        leg_id VARCHAR,
                        c_name VARCHAR,
                        p_name VARCHAR,
                        phone VARCHAR,
                        email VARCHAR,
                        prod_id INT,
                        prod_str VARCHAR,
                        src_id INT,
                        raw_src VARCHAR,
                        territory VARCHAR,
                        industry VARCHAR,
                        street VARCHAR,
                        city VARCHAR,
                        description TEXT,
                        deal_size NUMERIC,
                        tob VARCHAR,
                        demo_done VARCHAR,
                        demo_type VARCHAR,
                        quote_date DATE,
                        technician VARCHAR,
                        user_id INT,
                        c_uid INT,
                        creation_date TIMESTAMP
                    ) ON COMMIT DROP;
                    TRUNCATE tmp_lead_update;
                """)
                for i in range(0, len(leads_to_update), 5000):
                    chunk = leads_to_update[i:i+5000]
                    execute_values(self.env.cr, """
                        INSERT INTO tmp_lead_update (leg_id, c_name, p_name, phone, email, prod_id, prod_str, src_id, raw_src, territory, industry, street, city, description, deal_size, tob, demo_done, demo_type, quote_date, technician, user_id, c_uid, creation_date)
                        VALUES %s
                    """, chunk)
                
                self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_tmp_lead_update_leg ON tmp_lead_update (leg_id);")
                
                self.env.cr.execute("""
                    UPDATE crm_lead AS l
                    SET contact_name = CASE WHEN (l.contact_name IS NULL OR l.contact_name = '') AND v.c_name IS NOT NULL THEN v.c_name ELSE l.contact_name END,
                        partner_name = CASE WHEN (l.partner_name IS NULL OR l.partner_name = '') AND v.p_name IS NOT NULL THEN v.p_name ELSE l.partner_name END,
                        phone = CASE WHEN (l.phone IS NULL OR l.phone = '') AND v.phone IS NOT NULL THEN v.phone ELSE l.phone END,
                        email_from = CASE WHEN (l.email_from IS NULL OR l.email_from = '') AND v.email IS NOT NULL THEN v.email ELSE l.email_from END,
                        crm_product_id = CASE WHEN l.crm_product_id IS NULL AND v.prod_id IS NOT NULL THEN v.prod_id ELSE l.crm_product_id END,
                        custom_product = CASE WHEN (l.custom_product IS NULL OR l.custom_product = '') AND v.prod_str IS NOT NULL THEN v.prod_str ELSE l.custom_product END,
                        source_id = CASE WHEN l.source_id IS NULL AND v.src_id IS NOT NULL THEN v.src_id ELSE l.source_id END,
                        custom_lead_source = CASE WHEN (l.custom_lead_source IS NULL OR l.custom_lead_source = '') AND v.raw_src IS NOT NULL THEN v.raw_src ELSE l.custom_lead_source END,
                        custom_territory = CASE WHEN (l.custom_territory IS NULL OR l.custom_territory = '') AND v.territory IS NOT NULL THEN v.territory ELSE l.custom_territory END,
                        custom_industry = CASE WHEN (l.custom_industry IS NULL OR l.custom_industry = '') AND v.industry IS NOT NULL THEN v.industry ELSE l.custom_industry END,
                        street = CASE WHEN (l.street IS NULL OR l.street = '') AND v.street IS NOT NULL THEN v.street ELSE l.street END,
                        city = CASE WHEN (l.city IS NULL OR l.city = '') AND v.city IS NOT NULL THEN v.city ELSE l.city END,
                        description = CASE WHEN (l.description IS NULL OR l.description = '') AND v.description IS NOT NULL THEN v.description ELSE l.description END,
                        expected_revenue = CASE WHEN (l.expected_revenue IS NULL OR l.expected_revenue = 0) AND v.deal_size > 0 THEN v.deal_size ELSE l.expected_revenue END,
                        custom_deal_size = CASE WHEN (l.custom_deal_size IS NULL OR l.custom_deal_size = 0) AND v.deal_size > 0 THEN v.deal_size ELSE l.custom_deal_size END,
                        custom_type_of_business = CASE WHEN (l.custom_type_of_business IS NULL OR l.custom_type_of_business = '') AND v.tob IS NOT NULL THEN v.tob ELSE l.custom_type_of_business END,
                        custom_demo_done = CASE WHEN (l.custom_demo_done IS NULL OR l.custom_demo_done = '' OR l.custom_demo_done = 'no') AND v.demo_done = 'yes' THEN 'yes' ELSE l.custom_demo_done END,
                        custom_demo_type = CASE WHEN (l.custom_demo_type IS NULL OR l.custom_demo_type = '' OR l.custom_demo_type = 'N/A') AND v.demo_type != 'N/A' THEN v.demo_type ELSE l.custom_demo_type END,
                        custom_quote_date = CASE WHEN l.custom_quote_date IS NULL AND v.quote_date IS NOT NULL THEN v.quote_date ELSE l.custom_quote_date END,
                        custom_technician = CASE WHEN (l.custom_technician IS NULL OR l.custom_technician = '') AND v.technician IS NOT NULL THEN v.technician ELSE l.custom_technician END,
                        user_id = COALESCE(v.user_id, l.user_id),
                        create_uid = COALESCE(v.c_uid, l.create_uid),
                        create_date = COALESCE(v.creation_date, l.create_date)
                    FROM tmp_lead_update v
                    WHERE l.custom_naming_series = v.leg_id;
                """)
                updated = len(leads_to_update)

            # ── Multi-Pass Reconciliation Loop (Loop until convergence / 0 changes) ──
            reconciliation_passes = 0
            while reconciliation_passes < 3:
                reconciliation_passes += 1
                changes_made = 0

                # Loop A: Re-link CRM Products
                self.env.cr.execute("""
                    INSERT INTO crm_product (name)
                    SELECT DISTINCT TRIM(custom_product)
                    FROM crm_lead
                    WHERE custom_product IS NOT NULL AND TRIM(custom_product) != ''
                      AND LOWER(TRIM(custom_product)) NOT IN (SELECT LOWER(TRIM(name)) FROM crm_product)
                    ON CONFLICT DO NOTHING;
                """)
                self.env.cr.execute("""
                    UPDATE crm_lead l
                    SET crm_product_id = p.id
                    FROM crm_product p
                    WHERE LOWER(TRIM(l.custom_product)) = LOWER(TRIM(p.name))
                      AND l.crm_product_id IS NULL;
                """)
                changes_made += self.env.cr.rowcount

                # Loop B: Re-link UTM Lead Sources
                self.env.cr.execute("""
                    INSERT INTO utm_source (name)
                    SELECT DISTINCT TRIM(custom_lead_source)
                    FROM crm_lead
                    WHERE custom_lead_source IS NOT NULL AND TRIM(custom_lead_source) != ''
                      AND LOWER(TRIM(custom_lead_source)) NOT IN (SELECT LOWER(TRIM(name)) FROM utm_source)
                    ON CONFLICT DO NOTHING;
                """)
                self.env.cr.execute("""
                    UPDATE crm_lead l
                    SET source_id = s.id
                    FROM utm_source s
                    WHERE LOWER(TRIM(l.custom_lead_source)) = LOWER(TRIM(s.name))
                      AND l.source_id IS NULL;
                """)
                changes_made += self.env.cr.rowcount

                # Loop C: Re-link unlinked To-Dos to newly imported Leads
                self.env.cr.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM information_schema.tables WHERE table_name = 'todo_task'
                    );
                """)
                if self.env.cr.fetchone()[0]:
                    self.env.cr.execute("""
                        UPDATE todo_task t
                        SET lead_id = l.id
                        FROM crm_lead l
                        WHERE (t.reference_name = l.custom_naming_series OR t.name = l.custom_naming_series)
                          AND t.lead_id IS NULL;
                    """)
                    changes_made += self.env.cr.rowcount

                if changes_made == 0:
                    break

        elif self.import_type == 'todo':
            first_rec = records[0] if records else {}
            if 'lead_name' in first_rec or 'custom_deal_size_' in first_rec:
                raise UserError(_("The uploaded file appears to be a Leads file (Lead.csv), but you selected '3. To-Dos'. Please select '2. Leads'."))

            TodoTaskModel = self.env['todo.task'].sudo()
            has_legacy_id = 'legacy_id' in TodoTaskModel._fields
            has_ref_name = 'reference_name' in TodoTaskModel._fields
            has_ref_type = 'reference_type' in TodoTaskModel._fields

            # Fast fetch existing ToDo IDs directly from DB
            if has_legacy_id:
                self.env.cr.execute("SELECT legacy_id FROM todo_task WHERE legacy_id IS NOT NULL")
                existing_todos = set(r[0] for r in self.env.cr.fetchall() if r[0])
            else:
                self.env.cr.execute("SELECT name FROM todo_task WHERE name IS NOT NULL")
                existing_todos = set(r[0] for r in self.env.cr.fetchall() if r[0])
            
            # Fast fetch lead ID and user ID map in a single SQL query
            self.env.cr.execute("SELECT custom_naming_series, id, user_id FROM crm_lead WHERE custom_naming_series IS NOT NULL")
            lead_info_map = {r[0]: (r[1], r[2]) for r in self.env.cr.fetchall() if r[0]}
            
            # Get admin/activity info
            admin_user_id = 2
            self.env.cr.execute("SELECT id FROM mail_activity_type LIMIT 1")
            act_row = self.env.cr.fetchone()
            activity_type_id = act_row[0] if act_row else 1
            lead_model_id = self.env['ir.model']._get('crm.lead').id
            
            todos_to_create = []
            todos_to_update = []
            for r in records:
                legacy_id = _safe_str(r.get('name') or r.get('id'))
                if not legacy_id:
                    skipped += 1
                    continue
                
                erpnext_lead_id = _safe_str(r.get('reference_name'))
                lead_tuple = lead_info_map.get(erpnext_lead_id)
                lead_id = lead_tuple[0] if lead_tuple else False
                salesperson_id = lead_tuple[1] if (lead_tuple and lead_tuple[1]) else admin_user_id
                
                desc_raw = _safe_str(r.get('description'))
                desc = _clean_html(desc_raw)
                subj = desc[:80] if desc else 'Imported ToDo'
                subj = _clean_html(subj)
                creation_date = _clean_datetime(r.get('creation'))
                status_val = _safe_str(r.get('status'), 'Open')
                due_date = _clean_date(r.get('date'))
                allocated_to = _safe_str(r.get('owner'))

                if legacy_id in existing_todos:
                    todos_to_update.append((legacy_id, lead_id or None, due_date or None, desc or None, status_val or None, allocated_to or None))
                    continue
                
                existing_todos.add(legacy_id)
                
                todo_dict = {
                    'name': subj,
                    'status': status_val,
                    'allocated_to': allocated_to,
                    'lead_id': lead_id,
                    'date': due_date,
                    'description': desc,
                    'create_date': creation_date,
                    'legacy_create_date': creation_date,
                    '_salesperson_id': salesperson_id,
                }
                if has_legacy_id:
                    todo_dict['legacy_id'] = legacy_id
                if has_ref_name:
                    todo_dict['reference_name'] = erpnext_lead_id
                if has_ref_type:
                    todo_dict['reference_type'] = _safe_str(r.get('reference_type'))
                todos_to_create.append(todo_dict)
                
            if todos_to_create:
                for i in range(0, len(todos_to_create), 500):
                    batch = todos_to_create[i:i+500]
                    orm_batch = []
                    for b in batch:
                        b_copy = dict(b)
                        b_copy.pop('_salesperson_id', None)
                        orm_batch.append(b_copy)
                        
                    created_recs = self.env['todo.task'].sudo().with_context(
                        mail_create_nolog=True,
                        mail_create_nosubscribe=True,
                        tracking_disable=True,
                        prefetch_fields=False
                    ).create(orm_batch)
                    
                    activities_to_create = []
                    for idx, rec in enumerate(created_recs):
                        if rec.legacy_create_date:
                            self.env.cr.execute("UPDATE todo_task SET create_date=%s WHERE id=%s", (rec.legacy_create_date, rec.id))
                        
                        # Generate native mail.activity for open tasks linked to leads
                        if rec.status == 'Open' and rec.lead_id:
                            salesperson_id = batch[idx].get('_salesperson_id') or admin_user_id
                            activities_to_create.append({
                                'res_model_id': lead_model_id,
                                'res_id': rec.lead_id.id,
                                'res_model': 'crm.lead',
                                'activity_type_id': activity_type_id,
                                'summary': (rec.name or '')[:250],
                                'note': rec.description if rec.description and rec.description != rec.name else False,
                                'date_deadline': rec.date or fields.Date.context_today(self),
                                'user_id': salesperson_id,
                                'active': True,
                            })
                            
                    if activities_to_create:
                        self.env['mail.activity'].sudo().with_context(
                            mail_create_nolog=True,
                            mail_create_nosubscribe=True,
                            tracking_disable=True
                        ).create(activities_to_create)
                        
                    created += len(batch)

            if todos_to_update:
                from psycopg2.extras import execute_values
                self.env.cr.execute("""
                    CREATE TEMP TABLE IF NOT EXISTS tmp_todo_update (
                        leg_id VARCHAR,
                        lead_id INT,
                        due_date DATE,
                        description TEXT,
                        status VARCHAR,
                        allocated_to VARCHAR
                    ) ON COMMIT DROP;
                    TRUNCATE tmp_todo_update;
                """)
                for i in range(0, len(todos_to_update), 5000):
                    chunk = todos_to_update[i:i+5000]
                    execute_values(self.env.cr, """
                        INSERT INTO tmp_todo_update (leg_id, lead_id, due_date, description, status, allocated_to)
                        VALUES %s
                    """, chunk)
                
                self.env.cr.execute("CREATE INDEX IF NOT EXISTS idx_tmp_todo_update_leg ON tmp_todo_update (leg_id);")
                
                if has_legacy_id:
                    self.env.cr.execute("""
                        UPDATE todo_task AS t
                        SET lead_id = COALESCE(t.lead_id, v.lead_id),
                            date = COALESCE(t.date, v.due_date),
                            description = CASE WHEN (t.description IS NULL OR t.description = '') THEN v.description ELSE t.description END,
                            status = CASE WHEN (t.status IS NULL OR t.status = '') THEN v.status ELSE t.status END,
                            allocated_to = CASE WHEN (t.allocated_to IS NULL OR t.allocated_to = '') THEN v.allocated_to ELSE t.allocated_to END
                        FROM tmp_todo_update v
                        WHERE t.legacy_id = v.leg_id;
                    """)
                else:
                    self.env.cr.execute("""
                        UPDATE todo_task AS t
                        SET lead_id = COALESCE(t.lead_id, v.lead_id),
                            date = COALESCE(t.date, v.due_date),
                            description = CASE WHEN (t.description IS NULL OR t.description = '') THEN v.description ELSE t.description END,
                            status = CASE WHEN (t.status IS NULL OR t.status = '') THEN v.status ELSE t.status END,
                            allocated_to = CASE WHEN (t.allocated_to IS NULL OR t.allocated_to = '') THEN v.allocated_to ELSE t.allocated_to END
                        FROM tmp_todo_update v
                        WHERE t.name = v.leg_id;
                    """)
                updated = len(todos_to_update)

            # ── Fast Reconciliation (Index-accelerated) ──
            # Re-link unlinked To-Dos by custom_naming_series
            self.env.cr.execute("""
                UPDATE todo_task t
                SET lead_id = l.id
                FROM crm_lead l
                WHERE t.reference_name = l.custom_naming_series
                  AND t.lead_id IS NULL;
            """)
            self.env.cr.execute("""
                UPDATE todo_task t
                SET lead_id = l.id
                FROM crm_lead l
                WHERE t.name = l.custom_naming_series
                  AND t.lead_id IS NULL;
            """)

            # Fast sync missing mail.activity records for open to-dos linked to leads
            self.env.cr.execute("""
                SELECT t.id, t.name, t.description, t.date, t.lead_id, COALESCE(l.user_id, %s)
                FROM todo_task t
                JOIN crm_lead l ON t.lead_id = l.id
                WHERE t.status = 'Open'
                  AND NOT EXISTS (
                      SELECT 1 FROM mail_activity a 
                      WHERE a.res_model = 'crm.lead' AND a.res_id = l.id AND a.summary = SUBSTRING(t.name FROM 1 FOR 250)
                  )
                LIMIT 500;
            """, (admin_user_id,))
            missing_acts = self.env.cr.fetchall()
            if missing_acts:
                acts_to_insert = []
                for m in missing_acts:
                    acts_to_insert.append({
                        'res_model_id': lead_model_id,
                        'res_id': m[4],
                        'res_model': 'crm.lead',
                        'activity_type_id': activity_type_id,
                        'summary': (m[1] or '')[:250],
                        'note': m[2] if m[2] and m[2] != m[1] else False,
                        'date_deadline': m[3] or fields.Date.context_today(self),
                        'user_id': m[5] or admin_user_id,
                        'active': True,
                    })
                if acts_to_insert:
                    self.env['mail.activity'].sudo().with_context(
                        mail_create_nolog=True,
                        mail_create_nosubscribe=True,
                        tracking_disable=True
                    ).create(acts_to_insert)

        summary_parts = []
        if created:
            summary_parts.append(f"created {created:,} new records")
        if updated:
            summary_parts.append(f"updated {updated:,} existing records")
        if skipped:
            summary_parts.append(f"skipped {skipped:,} records")
        if not summary_parts:
            summary_parts.append(f"verified {len(records):,} records (all 100% matched and reconciled)")

        msg = _(f"Import & Reconciliation Complete! Successfully {', '.join(summary_parts)} across all fields.")
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import & Reconciliation Summary'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            }
        }
