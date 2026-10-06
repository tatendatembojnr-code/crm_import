DROP VIEW IF EXISTS crm_activity_log CASCADE;

CREATE OR REPLACE VIEW crm_activity_log AS (
    WITH new_leads AS (
        SELECT 
            COALESCE(create_uid, user_id) AS user_id,
            COUNT(id) AS count
        FROM crm_lead
        WHERE COALESCE(create_uid, user_id) IS NOT NULL
        GROUP BY COALESCE(create_uid, user_id)
    ),
    updated_leads AS (
        SELECT 
            u.actor_id AS user_id,
            COUNT(DISTINCT u.lead_id) AS count
        FROM (
            SELECT write_uid AS actor_id, id AS lead_id 
            FROM crm_lead 
            WHERE write_uid != create_uid AND write_uid IS NOT NULL
            UNION
            SELECT create_uid AS actor_id, res_id AS lead_id 
            FROM mail_activity 
            WHERE res_model = 'crm.lead' AND create_uid IS NOT NULL
            UNION
            SELECT (SELECT res_users.id FROM res_users WHERE res_users.partner_id = m.author_id LIMIT 1) AS actor_id, 
                   m.res_id AS lead_id 
            FROM mail_message m 
            WHERE m.model = 'crm.lead' AND m.author_id IS NOT NULL
            UNION
            SELECT create_uid AS actor_id, lead_id 
            FROM todo_task 
            WHERE lead_id IS NOT NULL AND create_uid IS NOT NULL
        ) u
        WHERE u.actor_id IS NOT NULL
        GROUP BY u.actor_id
    )
    SELECT 
        usr.id AS id,
        usr.id AS user_id,
        COALESCE(nl.count, 0) AS new_leads_count,
        COALESCE(ul.count, 0) AS updated_leads_count,
        (COALESCE(nl.count, 0) + COALESCE(ul.count, 0)) AS total_count
    FROM res_users usr
    LEFT JOIN new_leads nl ON nl.user_id = usr.id
    LEFT JOIN updated_leads ul ON ul.user_id = usr.id
    WHERE usr.active IS TRUE 
      AND (COALESCE(nl.count, 0) > 0 OR COALESCE(ul.count, 0) > 0)
);

SELECT id, user_id, new_leads_count, updated_leads_count, total_count FROM crm_activity_log ORDER BY total_count DESC;
