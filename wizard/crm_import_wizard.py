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
        ('lead', '2. Leads'),
        ('todo', '3. To-Dos'),
    ], string='What are you importing?', required=True, default='user')

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

        elif self.import_type == 'lead':
            # Pre-fetch existing lead IDs to skip fast
            all_legacy_ids = [_safe_str(r.get('name') or r.get('id')) for r in records if _safe_str(r.get('name') or r.get('id'))]
            existing_leads = set(self.env['crm.lead'].sudo().with_context(active_test=False).search([('custom_naming_series', 'in', all_legacy_ids)]).mapped('custom_naming_series'))
            
            # Pre-fetch users for fast mapping
            user_map = {u.login: u.id for u in self.env['res.users'].sudo().with_context(active_test=False).search([])}
            
            leads_to_create = []
            for r in records:
                legacy_id = _safe_str(r.get('name') or r.get('id'))
                if not legacy_id or legacy_id in existing_leads:
                    skipped += 1
                    continue
                
                existing_leads.add(legacy_id)
                orig_name = _safe_str(r.get('first_name') or r.get('lead_name'))
                company_name = _safe_str(r.get('company_name'))
                territory = _safe_str(r.get('territory'))
                product = _safe_str(r.get('custom_product'))
                
                parts = []
                if orig_name: parts.append(orig_name)
                if company_name: parts.append(company_name)
                if territory: parts.append(territory)
                
                title = " ".join(parts).strip()
                if product:
                    title = f"{title} - {product}" if title else product
                if not title:
                    title = "Unknown Lead"
                
                status_val = _safe_str(r.get('status'))
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

                owner_email = _safe_str(r.get('owner'))
                user_id = user_map.get(owner_email, False)
                creation_date = _clean_datetime(r.get('creation'))
                
                deal_size = 0.0
                try: deal_size = float(r.get('custom_deal_size_') or 0)
                except: pass

                leads_to_create.append({
                    'name': title,
                    'partner_name': company_name,
                    'phone': _safe_str(r.get('mobile_no')),
                    'email_from': _safe_str(r.get('email_id')),
                    'custom_naming_series': legacy_id,
                    'custom_lead_source': _safe_str(r.get('source')),
                    'custom_territory': _safe_str(r.get('territory')),
                    'custom_industry': _safe_str(r.get('industry')),
                    'custom_product': _safe_str(r.get('custom_product')),
                    'expected_revenue': deal_size,
                    'custom_deal_size': deal_size,
                    'custom_type_of_business': _safe_str(r.get('custom_type_of_business')),
                    'custom_quote_date': _clean_date(r.get('custom_quote_date')),
                    'custom_technician': _safe_str(r.get('custom_technician')),
                    'user_id': user_id,
                    'stage_id': stage_id,
                    'probability': probability,
                    'active': active,
                    'create_date': creation_date,
                    'legacy_create_date': creation_date,
                })
            
            if leads_to_create:
                # Use raw SQL to preserve create_date since ORM overrides it
                cr = self.env.cr
                for batch in [leads_to_create[i:i+500] for i in range(0, len(leads_to_create), 500)]:
                    # Native create to handle triggers/defaults, then raw SQL update for dates
                    created_recs = self.env['crm.lead'].sudo().with_context(mail_create_nolog=True, mail_create_nosubscribe=True, tracking_disable=True).create(batch)
                    for rec in created_recs:
                        if rec.legacy_create_date:
                            cr.execute("UPDATE crm_lead SET create_date=%s WHERE id=%s", (rec.legacy_create_date, rec.id))
                    created += len(batch)

        elif self.import_type == 'todo':
            # Pre-fetch existing ToDo IDs to skip fast (assuming name is the ID or we match on something)
            # Frappe Todos have a 'name' field which is the ID
            all_legacy_ids = [_safe_str(r.get('name') or r.get('id')) for r in records if _safe_str(r.get('name') or r.get('id'))]
            existing_todos = set(self.env['todo.task'].sudo().search([('legacy_id', 'in', all_legacy_ids)]).mapped('legacy_id'))
            
            # Pre-fetch leads for fast mapping
            all_lead_refs = [_safe_str(r.get('reference_name')) for r in records if _safe_str(r.get('reference_name'))]
            leads = self.env['crm.lead'].sudo().search_read([('custom_naming_series', 'in', all_lead_refs)], ['id', 'custom_naming_series'])
            lead_map = {l['custom_naming_series']: l['id'] for l in leads}
            
            todos_to_create = []
            for r in records:
                legacy_id = _safe_str(r.get('name') or r.get('id'))
                if not legacy_id or legacy_id in existing_todos:
                    skipped += 1
                    continue
                
                existing_todos.add(legacy_id)
                erpnext_lead_id = _safe_str(r.get('reference_name'))
                lead_id = lead_map.get(erpnext_lead_id, False)
                
                desc_raw = _safe_str(r.get('description'))
                desc = _clean_html(desc_raw)
                subj = desc[:80] if desc else 'Imported ToDo'
                subj = _clean_html(subj)
                creation_date = _clean_datetime(r.get('creation'))
                
                todos_to_create.append({
                    'name': subj,
                    'legacy_id': legacy_id,
                    'status': _safe_str(r.get('status'), 'Open'),
                    'allocated_to': _safe_str(r.get('owner')),
                    'lead_id': lead_id,
                    'date': _clean_date(r.get('date')),
                    'description': desc,
                    'create_date': creation_date,
                    'legacy_create_date': creation_date,
                })
                
            if todos_to_create:
                cr = self.env.cr
                admin_user_id = 2
                activity_type_id = 4 # To-Do
                
                for batch in [todos_to_create[i:i+500] for i in range(0, len(todos_to_create), 500)]:
                    created_recs = self.env['todo.task'].sudo().with_context(mail_create_nolog=True).create(batch)
                    
                    activities_to_create = []
                    for rec in created_recs:
                        if rec.legacy_create_date:
                            cr.execute("UPDATE todo_task SET create_date=%s WHERE id=%s", (rec.legacy_create_date, rec.id))
                        
                        # Generate native mail.activity for open tasks linked to leads
                        if rec.status == 'Open' and rec.lead_id:
                            # Assign to lead's salesperson, fallback to admin
                            salesperson_id = rec.lead_id.user_id.id if rec.lead_id.user_id else admin_user_id
                            
                            activities_to_create.append({
                                'res_model_id': self.env['ir.model']._get('crm.lead').id,
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
                        self.env['mail.activity'].sudo().create(activities_to_create)
                        
                    created += len(batch)

        msg = _(f'Import Complete! Successfully created {created} new records and skipped {skipped} existing records.')
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': _('Import Summary'),
                'message': msg,
                'type': 'success',
                'sticky': True,
            }
        }
