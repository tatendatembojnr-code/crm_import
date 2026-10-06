import subprocess
import json

sql = """
-- 1. Check Leads and Salesperson coverage
SELECT 
    count(*) as total_leads,
    count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson,
    count(CASE WHEN create_uid IS NULL THEN 1 END) as leads_without_create_uid
FROM crm_lead;

-- 2. If any lead has NULL user_id, fix it immediately using create_uid or 2 (admin)
UPDATE crm_lead 
SET user_id = COALESCE(create_uid, 2) 
WHERE user_id IS NULL;

-- 3. Check To-Do tasks count and user_id / lead_id coverage
SELECT 
    count(*) as total_todos,
    count(CASE WHEN user_id IS NULL THEN 1 END) as todos_without_user,
    count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead,
    count(CASE WHEN date IS NULL AND legacy_create_date IS NULL AND create_date IS NULL THEN 1 END) as todos_without_date
FROM todo_task;

-- 4. If any todo has NULL user_id, inherit user_id from lead or create_uid
UPDATE todo_task t
SET user_id = COALESCE(l.user_id, t.create_uid, 2)
FROM crm_lead l
WHERE t.lead_id = l.id AND t.user_id IS NULL;

UPDATE todo_task
SET user_id = COALESCE(create_uid, 2)
WHERE user_id IS NULL;

-- 5. Check Mail Activities
SELECT 
    count(*) as total_activities,
    count(CASE WHEN user_id IS NULL THEN 1 END) as activities_without_user,
    count(CASE WHEN res_model = 'crm.lead' THEN 1 END) as crm_activities
FROM mail_activity;

-- 6. Check Mail Messages (Chatter / Notes)
SELECT 
    count(*) as total_lead_messages,
    count(CASE WHEN author_id IS NULL AND create_uid IS NULL THEN 1 END) as messages_without_author
FROM mail_message 
WHERE model = 'crm.lead';

-- 7. Distribution of leads per salesperson
SELECT 
    u.id as user_id,
    p.name as salesperson_name,
    count(l.id) as total_leads,
    count(t.id) as total_todos
FROM res_users u
JOIN res_partner p ON u.partner_id = p.id
LEFT JOIN crm_lead l ON l.user_id = u.id
LEFT JOIN todo_task t ON t.user_id = u.id
GROUP BY u.id, p.name
HAVING count(l.id) > 0 OR count(t.id) > 0
ORDER BY total_leads DESC;

-- 8. Verify remaining nulls after update
SELECT 
    (SELECT count(*) FROM crm_lead WHERE user_id IS NULL) as remaining_leads_without_salesperson,
    (SELECT count(*) FROM todo_task WHERE user_id IS NULL) as remaining_todos_without_user;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

print("Running full audit and fix on showline database...")
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
if res.stderr:
    print("STDERR:\n", res.stderr)
