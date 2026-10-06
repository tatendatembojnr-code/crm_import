import subprocess

sql = """
INSERT INTO crm_lead (name, contact_name, partner_name, user_id, type, active, create_date, priority)
SELECT DISTINCT 
    COALESCE(t.reference_name, t.name),
    COALESCE(t.reference_name, t.name),
    COALESCE(t.reference_name, t.name),
    COALESCE(u.id, 2),
    'opportunity',
    true,
    COALESCE(t.legacy_create_date, t.create_date, NOW()),
    '1'
FROM todo_task t
LEFT JOIN res_users u ON (u.login = t.allocated_to OR u.name = t.allocated_to)
WHERE t.lead_id IS NULL;

UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
WHERE t.lead_id IS NULL 
  AND (l.name = t.reference_name OR l.name = t.name);

UPDATE crm_lead SET user_id = COALESCE(create_uid, 2) WHERE user_id IS NULL;

SELECT count(*) as total_leads, count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson FROM crm_lead;
SELECT count(*) as total_todos, count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead FROM todo_task;
"""

cmd = f'docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c "{sql}"'
res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
print("STDERR:\n", res.stderr)
