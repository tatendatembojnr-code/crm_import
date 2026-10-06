# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class CrmActivityLog(models.Model):
    _name = 'crm.activity.log'
    _description = 'Salesperson Activity Log'
    _auto = False
    _order = 'activity_date desc, total_count desc, user_id asc'

    activity_date = fields.Date(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    new_leads_count = fields.Integer(string='New Leads', readonly=True)
    updated_leads_count = fields.Integer(string='Updated Leads', readonly=True)
    total_count = fields.Integer(string='Total', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW crm_activity_log AS (
                WITH raw_events AS (
                    -- Leads created
                    SELECT 
                        COALESCE(create_uid, user_id) AS user_id,
                        (create_date AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        id AS lead_id,
                        1 AS is_new
                    FROM crm_lead
                    WHERE COALESCE(create_uid, user_id) IS NOT NULL AND create_date IS NOT NULL
                    
                    UNION ALL
                    
                    -- Leads updated
                    SELECT 
                        write_uid AS user_id,
                        (write_date AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        id AS lead_id,
                        0 AS is_new
                    FROM crm_lead
                    WHERE write_uid IS NOT NULL AND write_date IS NOT NULL AND write_date != create_date
                    
                    UNION ALL
                    
                    -- Mail activities on CRM leads
                    SELECT 
                        COALESCE(user_id, create_uid) AS user_id,
                        (create_date AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        res_id AS lead_id,
                        0 AS is_new
                    FROM mail_activity
                    WHERE res_model = 'crm.lead' AND create_date IS NOT NULL
                    
                    UNION ALL
                    
                    -- Chatter messages / calls / notes logged on CRM leads
                    SELECT 
                        (SELECT ru.id FROM res_users ru WHERE ru.partner_id = m.author_id LIMIT 1) AS user_id,
                        (m.create_date AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        res_id AS lead_id,
                        0 AS is_new
                    FROM mail_message m
                    WHERE m.model = 'crm.lead' AND m.create_date IS NOT NULL AND m.author_id IS NOT NULL
                    
                    UNION ALL
                    
                    -- To-Dos created / assigned
                    SELECT 
                        create_uid AS user_id,
                        (create_date AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        lead_id,
                        0 AS is_new
                    FROM todo_task
                    WHERE create_date IS NOT NULL AND create_uid IS NOT NULL AND lead_id IS NOT NULL
                ),
                unique_daily_leads AS (
                    SELECT 
                        user_id,
                        activity_date,
                        lead_id,
                        MAX(is_new) AS is_new
                    FROM raw_events
                    WHERE user_id IS NOT NULL AND lead_id IS NOT NULL
                    GROUP BY user_id, activity_date, lead_id
                )
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY u.activity_date DESC, COUNT(u.lead_id) DESC, u.user_id ASC) AS id,
                    u.user_id AS user_id,
                    u.activity_date AS activity_date,
                    COUNT(CASE WHEN u.is_new = 1 THEN u.lead_id END) AS new_leads_count,
                    COUNT(CASE WHEN u.is_new = 0 THEN u.lead_id END) AS updated_leads_count,
                    COUNT(u.lead_id) AS total_count
                FROM unique_daily_leads u
                JOIN res_users ru ON ru.id = u.user_id
                WHERE ru.active IS TRUE
                GROUP BY u.user_id, u.activity_date
            )
        """)
