from odoo import models, fields, api

# Quick-message buttons: status key -> (button label, log sentence)
QUICK_RESPONSES = {
    'no_answer': ('No Answer', 'The customer did not answer'),
    'not_reachable': ('Not Reachable', 'The customer is not reachable'),
    'no_first_call': ('No Answer (1st Call)', 'The customer did not answer the first call'),
}


class CrmLead(models.Model):
    _inherit = 'crm.lead'
    _order = 'priority desc, create_date desc, id desc'

    @api.model
    def web_read_group(self, domain, groupby, aggregates=(), limit=None, offset=0, order=None, **kwargs):
        # When grouping by create_date (day, month, week, year), default order to descending (latest first)
        # and expand limit to show all groups across all records (e.g. 597 days) without 80-limit cutoff
        if groupby and any(isinstance(g, str) and 'create_date' in g for g in groupby):
            if not order:
                order = 'create_date desc'
            if not limit or limit == 80:
                limit = 2000
            kwargs.setdefault('unfold_read_default_limit', 500)

        return super().web_read_group(
            domain, groupby, aggregates=aggregates, limit=limit, offset=offset, order=order, **kwargs
        )

    @api.model
    def _read_group(self, domain, groupby=(), aggregates=(), having=(), offset=0, limit=None, order=None):
        if groupby and any(isinstance(g, str) and 'create_date' in g for g in groupby):
            if not order:
                order = 'create_date desc'
            if not limit or limit == 80:
                limit = 2000
        return super()._read_group(
            domain, groupby=groupby, aggregates=aggregates, having=having, offset=offset, limit=limit, order=order
        )
    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if not vals.get('user_id'):
                vals['user_id'] = self.env.uid
        leads = super().create(vals_list)
        for lead in leads:
            lead._ensure_lead_activity()
        return leads

    def write(self, vals):
        res = super().write(vals)
        if any(f in vals for f in ('custom_next_contact_date', 'user_id', 'active', 'probability')):
            for lead in self:
                lead._ensure_lead_activity()
        return res

    def _ensure_lead_activity(self):
        """Ensure that every active lead with a Next Contact Date has a matching open To-Do activity and chatter log note."""
        self.ensure_one()
        if not self.active:
            return

        target_date = self.custom_next_contact_date
        if not target_date:
            return

        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not todo_type:
            todo_type = self.env['mail.activity.type'].search([
                '|', ('res_model', '=', False), ('res_model', '=', 'crm.lead'),
                ('category', '=', 'default')
            ], limit=1)

        open_activities = self.activity_ids.filtered(lambda a: a.date_deadline)
        if open_activities:
            for act in open_activities:
                vals = {}
                if act.date_deadline != target_date:
                    vals['date_deadline'] = target_date
                if act.summary != 'To-Do':
                    vals['summary'] = 'To-Do'
                if not act.note or 'Next Contact Date' not in act.note:
                    vals['note'] = '<p>Next Contact Date</p>'
                if vals:
                    act.sudo().write(vals)
        else:
            self.env['mail.activity'].sudo().create({
                'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                'res_id': self.id,
                'activity_type_id': todo_type.id if todo_type else False,
                'summary': 'To-Do',
                'date_deadline': target_date,
                'user_id': self.user_id.id if self.user_id else self.env.uid,
                'note': '<p>Next Contact Date</p>',
            })

        # Post log note in chatter
        formatted_date = target_date.strftime('%d/%m/%Y') if hasattr(target_date, 'strftime') else str(target_date)
        log_body = f"<strong>Next Contact Date:</strong> {formatted_date}"
        recent_msg = self.message_ids.filtered(
            lambda m: m.subtype_id == self.env.ref('mail.mt_note', raise_if_not_found=False) and log_body in (m.body or '')
        )
        if not recent_msg:
            self.message_post(body=log_body, subtype_xmlid='mail.mt_note')

    def action_send_email_composer(self):
        self.ensure_one()
        template_id = self.env['ir.model.data']._xmlid_to_res_id('crm.email_template_opportunity_mail', raise_if_not_found=False)
        ctx = {
            'default_model': 'crm.lead',
            'default_res_ids': self.ids,
            'default_composition_mode': 'comment',
            'default_use_template': bool(template_id),
            'default_template_id': template_id,
            'force_email': True,
        }
        return {
            'type': 'ir.actions.act_window',
            'name': 'Compose Email',
            'view_mode': 'form',
            'res_model': 'mail.compose.message',
            'views': [(False, 'form')],
            'view_id': False,
            'target': 'new',
            'context': ctx,
        }

    def action_send_sms_composer(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Send SMS',
            'view_mode': 'form',
            'res_model': 'sms.composer',
            'target': 'new',
            'context': {
                'default_res_model': 'crm.lead',
                'default_res_id': self.id,
                'default_number_field_name': 'phone',
                'default_composition_mode': 'comment',
            },
        }

    # ── ERPNext Legacy Fields ──────────────────────────────────────────────────
    custom_naming_series   = fields.Char(string='Legacy ID (ERPNext)')
    custom_lead_source     = fields.Char(string='Lead Source (Legacy)')
    custom_territory       = fields.Char(string='Territory')
    custom_industry        = fields.Char(string='Industry')

    # Product & Deal Info — standalone crm.product, NO relation to product.product
    crm_product_id         = fields.Many2one(
        'crm.product',
        string='Product Interest',
        ondelete='set null',
        help='CRM product representing the customer interest (independent of inventory catalog).'
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
    custom_demo_done       = fields.Selection([
        ('no', 'No'),
        ('yes', 'Yes'),
    ], string='Demo Done', default='no')
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

    # Next Contact & Quick Responses
    custom_next_contact_date = fields.Date(string="Next Contact Date", tracking=True)
    custom_response_status = fields.Selection([
        ('normal', 'Normal Response'),
        ('no_answer', 'No Answer'),
        ('not_reachable', 'Not Reachable'),
        ('no_first_call', 'Not Answering First Time Call'),
    ], string='Response Status', default='normal', tracking=True)

    def action_set_response_no_answer(self):
        return self._open_quick_response_wizard('no_answer')

    def action_set_response_not_reachable(self):
        return self._open_quick_response_wizard('not_reachable')

    def action_set_response_no_first_call(self):
        return self._open_quick_response_wizard('no_first_call')

    def _open_quick_response_wizard(self, status):
        """Open the standard 'Schedule an Activity' dialog pre-filled for a quick response."""
        self.ensure_one()
        from datetime import timedelta
        label, log_sentence = QUICK_RESPONSES.get(status, (status, 'Follow-up scheduled'))
        tomorrow = fields.Date.context_today(self) + timedelta(days=1)

        todo_type = self.env.ref('mail.mail_activity_data_todo', raise_if_not_found=False)
        if not todo_type:
            todo_type = self.env['mail.activity.type'].search([
                '|', ('res_model', '=', False), ('res_model', '=', 'crm.lead'),
                ('category', '=', 'default')
            ], limit=1)

        ctx = {
            'active_model': 'crm.lead',
            'active_ids': self.ids,
            'active_id': self.id,
            'crm_quick_response': status,
            'crm_quick_response_label': label,
            'crm_quick_response_log': log_sentence,
            'default_summary': 'To-Do',
            'default_note': f'<p>{label}</p>',
            'default_date_deadline': tomorrow,
            'dialog_size': 'large',
        }
        if todo_type:
            ctx['default_activity_type_id'] = todo_type.id
        if self.user_id:
            ctx['default_activity_user_id'] = self.user_id.id

        return {
            'type': 'ir.actions.act_window',
            'name': f'Schedule an Activity - {label}',
            'res_model': 'mail.activity.schedule',
            'view_mode': 'form',
            'views': [(False, 'form')],
            'target': 'new',
            'context': ctx,
        }




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
                            inner_text = re.sub(r'<[^>]+>', ' ', html.unescape(inner_match.group(1))).strip()
                            inner_text = re.sub(r'\s+', ' ', inner_text).strip()
                        else:
                            inner_text = ''
                        
                        clean_text = re.sub(r'<[^>]+>', ' ', html.unescape(m.body)).strip()
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
                    cleaned_note = (re.sub(r'<[^>]+>', ' ', html.unescape(a.note or '')).strip() if a.note else '')
                    cleaned_note = re.sub(r'\s+', ' ', cleaned_note).strip()
                    
                    summary_text = (re.sub(r'<[^>]+>', ' ', html.unescape(a.summary or '')).strip() if a.summary else '')
                    summary_text = re.sub(r'\s+', ' ', summary_text).strip()
                    
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
                    todo_desc = (re.sub(r'<[^>]+>', ' ', html.unescape(t.description or '')).strip() if t.description else '')
                    todo_desc = re.sub(r'\s+', ' ', todo_desc).strip()
                    
                    todo_name = (re.sub(r'<[^>]+>', ' ', html.unescape(str(t.name or ''))).strip() if t.name else '')
                    todo_name = re.sub(r'\s+', ' ', todo_name).strip()
                    
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


