# -*- coding: utf-8 -*-
from odoo import models, fields, tools

class CrmHourlyActivityLog(models.Model):
    _name = 'crm.hourly.activity.log'
    _description = 'Hourly Activity Log'
    _auto = False
    _order = 'activity_date desc, total_count desc, user_id asc'

    activity_date = fields.Date(string='Date', readonly=True)
    user_id = fields.Many2one('res.users', string='Salesperson', readonly=True)
    h08_09 = fields.Integer(string='8am to 9am', readonly=True)
    h09_10 = fields.Integer(string='9am to 10am', readonly=True)
    h10_11 = fields.Integer(string='10am to 11am', readonly=True)
    h11_12 = fields.Integer(string='11am to 12pm', readonly=True)
    h12_01 = fields.Integer(string='12pm to 1pm', readonly=True)
    h02_03 = fields.Integer(string='2pm to 3pm', readonly=True)
    h03_04 = fields.Integer(string='3pm to 4pm', readonly=True)
    h04_05 = fields.Integer(string='4pm to 5pm', readonly=True)
    total_count = fields.Integer(string='Total', readonly=True)

    def init(self):
        tools.drop_view_if_exists(self.env.cr, self._table)
        self.env.cr.execute("""
            CREATE OR REPLACE VIEW crm_hourly_activity_log AS (
                WITH raw_events AS (
                    -- Leads created
                    SELECT 
                        COALESCE(create_uid, user_id) AS user_id,
                        create_date AS event_time,
                        id AS lead_id
                    FROM crm_lead
                    WHERE COALESCE(create_uid, user_id) IS NOT NULL AND create_date IS NOT NULL
                    
                    UNION ALL
                    
                    -- Leads updated
                    SELECT 
                        write_uid AS user_id,
                        write_date AS event_time,
                        id AS lead_id
                    FROM crm_lead
                    WHERE write_uid IS NOT NULL AND write_date IS NOT NULL AND write_date != create_date
                    
                    UNION ALL
                    
                    -- Mail activities on CRM leads
                    SELECT 
                        COALESCE(user_id, create_uid) AS user_id,
                        create_date AS event_time,
                        res_id AS lead_id
                    FROM mail_activity
                    WHERE res_model = 'crm.lead' AND create_date IS NOT NULL
                    
                    UNION ALL
                    
                    -- Chatter messages / calls / notes logged on CRM leads
                    SELECT 
                        (SELECT ru.id FROM res_users ru WHERE ru.partner_id = m.author_id LIMIT 1) AS user_id,
                        m.create_date AS event_time,
                        res_id AS lead_id
                    FROM mail_message m
                    WHERE m.model = 'crm.lead' AND m.create_date IS NOT NULL AND m.author_id IS NOT NULL
                    
                    UNION ALL
                    
                    -- To-Dos created / assigned
                    SELECT 
                        create_uid AS user_id,
                        create_date AS event_time,
                        lead_id
                    FROM todo_task
                    WHERE create_date IS NOT NULL AND create_uid IS NOT NULL AND lead_id IS NOT NULL
                ),
                events_with_hour AS (
                    SELECT 
                        e.user_id,
                        e.lead_id,
                        (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg')::date AS activity_date,
                        EXTRACT(HOUR FROM (e.event_time AT TIME ZONE 'UTC' AT TIME ZONE 'Africa/Johannesburg'))::int AS hour_val
                    FROM raw_events e
                    WHERE e.user_id IS NOT NULL AND e.lead_id IS NOT NULL
                )
                SELECT 
                    ROW_NUMBER() OVER (ORDER BY eh.activity_date DESC, COUNT(DISTINCT eh.lead_id) DESC, eh.user_id ASC) AS id,
                    eh.user_id AS user_id,
                    eh.activity_date AS activity_date,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 8 THEN eh.lead_id END) AS h08_09,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 9 THEN eh.lead_id END) AS h09_10,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 10 THEN eh.lead_id END) AS h10_11,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 11 THEN eh.lead_id END) AS h11_12,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 12 THEN eh.lead_id END) AS h12_01,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 14 THEN eh.lead_id END) AS h02_03,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 15 THEN eh.lead_id END) AS h03_04,
                    COUNT(DISTINCT CASE WHEN eh.hour_val = 16 THEN eh.lead_id END) AS h04_05,
                    COUNT(DISTINCT eh.lead_id) AS total_count
                FROM events_with_hour eh
                JOIN res_users u ON u.id = eh.user_id
                WHERE u.active IS TRUE
                GROUP BY eh.user_id, eh.activity_date
            )
        """)
