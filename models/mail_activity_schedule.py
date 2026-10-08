# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import models, fields, api, _

class MailActivitySchedule(models.TransientModel):
    _inherit = 'mail.activity.schedule'

    crm_quick_response = fields.Char(string='CRM Quick Response')

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        qr = self.env.context.get('crm_quick_response')
        if qr:
            res['crm_quick_response'] = qr
            label = self.env.context.get('crm_quick_response_label')
            # The director requested task name (Summary) to be To-Do instead of No Answer
            res['summary'] = _('To-Do')
            # The log note will contain the No Answer / quick response details
            if label:
                res['note'] = f'<p>{label}</p>'
            tomorrow = fields.Date.context_today(self) + timedelta(days=1)
            res['date_deadline'] = tomorrow
        return res

    @api.depends('activity_type_id')
    def _compute_summary(self):
        super()._compute_summary()
        for record in self:
            if record.crm_quick_response or self.env.context.get('crm_quick_response'):
                record.summary = _('To-Do')

    def action_quick_schedule_tomorrow(self):
        target = fields.Date.context_today(self) + timedelta(days=1)
        return self._execute_schedule(target_date=target)

    def action_quick_schedule_next_week(self):
        target = fields.Date.context_today(self) + timedelta(days=7)
        return self._execute_schedule(target_date=target)

    def action_quick_schedule_two_weeks(self):
        target = fields.Date.context_today(self) + timedelta(days=14)
        return self._execute_schedule(target_date=target)

    def action_quick_schedule_one_month(self):
        target = fields.Date.context_today(self) + timedelta(days=30)
        return self._execute_schedule(target_date=target)

    def action_schedule_activities(self):
        qr_status = self.crm_quick_response or self.env.context.get('crm_quick_response')
        if qr_status and self.res_model == 'crm.lead':
            return self._execute_schedule()
        return super().action_schedule_activities()

    def _execute_schedule(self, target_date=None):
        self.ensure_one()
        if target_date:
            self.date_deadline = target_date

        deadline = self.date_deadline or fields.Date.context_today(self)
        qr_status = self.crm_quick_response or self.env.context.get('crm_quick_response')
        label = self.env.context.get('crm_quick_response_label') or qr_status

        # Ensure task name is To-Do
        self.summary = _('To-Do')

        if self.res_model == 'crm.lead':
            leads = self._get_applied_on_records()
            for lead in leads:
                # 1. Close/mark done any open activities currently on this lead
                existing_activities = lead.activity_ids

                log_prefix = self.env.context.get('crm_quick_response_log')
                if not log_prefix:
                    if qr_status == 'no_answer':
                        log_prefix = "The customer did not answer"
                    elif qr_status == 'not_reachable':
                        log_prefix = "The customer is not reachable"
                    elif qr_status == 'no_first_call':
                        log_prefix = "The customer did not answer (1st Call)"
                    else:
                        log_prefix = "Follow-up scheduled"

                feedback_msg = f"<strong>{label}:</strong> {log_prefix}. Next contact scheduled on {deadline}."
                if self.note and self.note.strip() and self.note.strip() not in ('<p><br></p>', '<p></p>', f'<p>{label}</p>'):
                    feedback_msg += f"<br/><strong>Note:</strong> {self.note}"

                if existing_activities:
                    existing_activities.action_feedback(feedback=feedback_msg)
                else:
                    lead.message_post(body=feedback_msg, subtype_xmlid='mail.mt_note')

                # 2. Close any open legacy todo.task records if present
                if hasattr(lead, 'todo_ids'):
                    lead.todo_ids.filtered(lambda t: t.status == 'Open').write({'status': 'Closed'})

                # 3. Update lead response status and mandatory next contact date
                vals = {'custom_next_contact_date': deadline}
                if qr_status:
                    vals['custom_response_status'] = qr_status
                lead.with_context(skip_ensure_activity=True).write(vals)

        # 4. Schedule the new activity
        return self._action_schedule_activities()
