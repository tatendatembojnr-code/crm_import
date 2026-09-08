from odoo import models, fields, api

class CrmLead(models.Model):
    _inherit = 'crm.lead'

    # ── ERPNext Legacy Fields ──────────────────────────────────────────────────
    custom_naming_series   = fields.Char(string='Legacy ID (ERPNext)')
    custom_lead_source     = fields.Char(string='Lead Source (Legacy)')
    custom_territory       = fields.Char(string='Territory')
    custom_industry        = fields.Char(string='Industry')

    # Product & Deal Info - Many2one selection to product catalog
    product_id             = fields.Many2one(
        'product.product',
        string='Product Interest',
        compute='_compute_product_id',
        readonly=False,
        help='Product catalog item representing the customer interest.'
    )
    custom_product         = fields.Char(string='Product Interest (Legacy)')
    custom_deal_size       = fields.Float(string='Deal Size')
    custom_type_of_business= fields.Char(string='Type of Business')

    # Quote Info
    custom_quote           = fields.Selection([
        ('Quote', 'Quoted'),
        ('Not yet Quoted', 'Not Yet Quoted'),
    ], string='Quote Status')
    custom_quote_date      = fields.Date(string='Quote Date')

    # Technician / Assignment
    custom_technician      = fields.Char(string='Technician Assigned')

    # Demo
    custom_demo_done       = fields.Boolean(string='Demo Done')
    custom_demo_type       = fields.Selection([
        ('Online', 'Online'),
        ('Onsite', 'Onsite'),
        ('N/A', 'N/A'),
    ], string='Demo Done Online or Onsite')

    # Proposal
    custom_proposal_status = fields.Selection([
        ('Not Yet', 'Not Yet'),
        ('Proposed', 'Proposed'),
        ('Accepted', 'Accepted'),
        ('Rejected', 'Rejected'),
    ], string='Proposal')
    custom_proposal_date   = fields.Date(string='Proposal Date')

    # Preserve actual dates from the old system
    legacy_create_date     = fields.Datetime(string='Original Creation Date')

    # Link to To-Do tasks
    todo_ids = fields.One2many('todo.task', 'lead_id', string='To-Do Tasks')

    # Computed latest Chatter message for list and form views (dynamic non-stored)
    last_chatter = fields.Text(
        string='Last Chatter',
        compute='_compute_last_chatter',
        help='Displays the latest chatter message, note, or activity on this lead.'
    )

    # Computed latest Activity / To-Do note for display in list views
    last_todo_note = fields.Text(
        string='Last To-Do / Note',
        compute='_compute_last_todo_note',
        help='Displays the most recent Activity or To-Do note attached to this lead.'
    )

    # My Deadline & Activity Deadline aligned with latest chatter / activity date
    my_activity_date_deadline = fields.Date(
        string='My Deadline',
        compute='_compute_my_activity_date_deadline',
        help='Deadline of the latest chatter message, activity, or To-Do on this lead.'
    )

    activity_date_deadline = fields.Date(
        string='Next Activity Deadline',
        compute='_compute_my_activity_date_deadline',
        help='Deadline of the latest chatter message, activity, or To-Do on this lead.'
    )

    @api.model
    def _find_or_create_product(self, product_name):
        if not product_name:
            return False
        clean_name = str(product_name).strip().strip('"')
        if not clean_name:
            return False
        
        Product = self.env['product.product'].sudo()
        prod = Product.search([('name', '=ilike', clean_name)], limit=1)
        if prod:
            return prod.id
        
        prod = Product.search([('default_code', '=ilike', clean_name)], limit=1)
        if prod:
            return prod.id
        
        try:
            new_prod = Product.create({
                'name': clean_name,
                'sale_ok': True,
                'purchase_ok': False,
            })
            return new_prod.id
        except Exception:
            return False

    @api.depends('custom_product', 'name')
    def _compute_product_id(self):
        for record in self:
            prod_name = False
            if record.custom_product and record.custom_product.strip():
                prod_name = record.custom_product.strip()
            elif record.name and ' - ' in record.name:
                parts = record.name.split(' - ')
                if len(parts) >= 2 and parts[-1].strip():
                    prod_name = parts[-1].strip()
            
            if prod_name:
                prod_id = self._find_or_create_product(prod_name)
                record.product_id = prod_id
            else:
                record.product_id = False

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('product_id'):
                prod_name = vals.get('custom_product')
                if not prod_name and vals.get('name') and ' - ' in str(vals['name']):
                    prod_name = str(vals['name']).split(' - ')[-1].strip()
                if prod_name:
                    prod_id = self._find_or_create_product(prod_name)
                    if prod_id:
                        vals['product_id'] = prod_id
        return super(CrmLead, self).create(vals_list)

    def write(self, vals):
        if ('custom_product' in vals or 'name' in vals) and not vals.get('product_id'):
            prod_name = vals.get('custom_product')
            if not prod_name and vals.get('name') and ' - ' in str(vals['name']):
                prod_name = str(vals['name']).split(' - ')[-1].strip()
            if prod_name:
                prod_id = self._find_or_create_product(prod_name)
                if prod_id:
                    vals['product_id'] = prod_id
        return super(CrmLead, self).write(vals)

    @api.depends('activity_ids', 'activity_ids.summary', 'activity_ids.note', 'activity_ids.date_deadline', 'todo_ids', 'todo_ids.name', 'todo_ids.description', 'todo_ids.date', 'message_ids', 'message_ids.body', 'message_ids.date')
    def _compute_last_chatter(self):
        import re
        import html
        for record in self:
            entries = []
            if record.message_ids:
                for m in record.message_ids:
                    if m.body:
                        # Extract inner note text if available
                        inner_match = re.search(r'</div>\s*<div>(.*)', m.body, re.DOTALL)
                        if inner_match:
                            inner_text = html.unescape(re.sub(r'<[^>]+>', ' ', inner_match.group(1))).strip()
                            inner_text = re.sub(r'\s+', ' ', inner_text).strip()
                        else:
                            inner_text = ''
                        
                        clean_text = html.unescape(re.sub(r'<[^>]+>', ' ', m.body)).strip()
                        clean_text = re.sub(r'\s+', ' ', clean_text).strip()
                        
                        # Strip standard To-Do boilerplate if present
                        if inner_text:
                            clean_text = inner_text
                        elif 'To-Do done :' in clean_text:
                            clean_text = clean_text.split('To-Do done :', 1)[-1].strip()
                            clean_text = re.sub(r'^T\d+\s*', '', clean_text).strip()
                        
                        if clean_text:
                            msg_date = m.date or m.create_date or False
                            entries.append((msg_date, m.id, clean_text[:250]))
            
            if record.activity_ids:
                for a in record.activity_ids:
                    cleaned_note = (html.unescape(re.sub(r'<[^>]+>', ' ', a.note or '')).strip() if a.note else '')
                    cleaned_note = re.sub(r'\s+', ' ', cleaned_note).strip()
                    summary_text = re.sub(r'\s+', ' ', a.summary or '').strip()
                    
                    # If summary looks like an ERPNext ID (e.g. T91974 or 10-char hash) and note is available, prefer note!
                    if cleaned_note and (not summary_text or (summary_text.startswith('T') and summary_text[1:].isdigit()) or len(summary_text) <= 12):
                        act_text = cleaned_note
                    else:
                        act_text = summary_text or cleaned_note

                    if act_text:
                        act_date = a.date_deadline or (a.create_date.date() if a.create_date else False) or False
                        entries.append((act_date, a.id, act_text[:250]))

            if record.todo_ids:
                for t in record.todo_ids:
                    todo_desc = (html.unescape(re.sub(r'<[^>]+>', ' ', t.description or '')).strip() if t.description else '')
                    todo_desc = re.sub(r'\s+', ' ', todo_desc).strip()
                    todo_name = re.sub(r'\s+', ' ', str(t.name or '')).strip()
                    if todo_desc and (not todo_name or (todo_name.startswith('T') and todo_name[1:].isdigit()) or len(todo_name) <= 12):
                        todo_text = todo_desc
                    else:
                        todo_text = todo_name or todo_desc

                    if todo_text:
                        todo_date = t.date or (t.legacy_create_date.date() if t.legacy_create_date else False) or (t.create_date.date() if t.create_date else False) or False
                        entries.append((todo_date, t.id, todo_text[:250]))

            if entries:
                sorted_entries = sorted(
                    entries,
                    key=lambda x: (str(x[0]) if x[0] else '', x[1]),
                    reverse=True
                )
                record.last_chatter = sorted_entries[0][2]
            else:
                record.last_chatter = False

    @api.depends('last_chatter')
    def _compute_last_todo_note(self):
        for record in self:
            record.last_todo_note = record.last_chatter

    @api.depends('activity_ids', 'activity_ids.date_deadline', 'activity_ids.create_date', 'message_ids', 'message_ids.date', 'todo_ids', 'todo_ids.date', 'todo_ids.legacy_create_date')
    def _compute_my_activity_date_deadline(self):
        for record in self:
            dates = []
            if record.activity_ids:
                for act in record.activity_ids:
                    if act.date_deadline:
                        dates.append(act.date_deadline)
                    elif act.create_date:
                        dates.append(act.create_date.date())
            if record.todo_ids:
                for todo in record.todo_ids:
                    if todo.date:
                        dates.append(todo.date)
                    elif todo.legacy_create_date:
                        dates.append(todo.legacy_create_date.date())
                    elif todo.create_date:
                        dates.append(todo.create_date.date())
            if record.message_ids:
                for msg in record.message_ids:
                    if msg.date:
                        dates.append(msg.date.date())
                    elif msg.create_date:
                        dates.append(msg.create_date.date())
            
            latest_date = max(dates) if dates else False
            record.my_activity_date_deadline = latest_date
            record.activity_date_deadline = latest_date
