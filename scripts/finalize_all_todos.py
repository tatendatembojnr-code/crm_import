import subprocess

sql = """
-- 1. Match Lead016777 -> lead 16777 or custom_naming_series
UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
WHERE t.id = 241850 AND (
    l.custom_naming_series ILIKE '%16777%' 
    OR l.id = 16777 
    OR l.name ILIKE '%16777%'
);

-- 2. Match Customer reference_name to crm_lead (partner_name / contact_name / name / res_partner)
UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
LEFT JOIN res_partner p ON l.partner_id = p.id
WHERE t.lead_id IS NULL
  AND t.reference_type = 'Customer'
  AND (
      l.partner_name ILIKE '%' || t.reference_name || '%'
      OR l.contact_name ILIKE '%' || t.reference_name || '%'
      OR l.name ILIKE '%' || t.reference_name || '%'
      OR p.name ILIKE '%' || t.reference_name || '%'
  );

-- 3. For any remaining Customer/Issue To-Dos without a lead, create a dedicated CRM Lead so nothing is orphaned
DO $$
DECLARE
    r RECORD;
    new_lead_id INT;
    uid_val INT;
BEGIN
    FOR r IN SELECT id, name, reference_type, reference_name, allocated_to, description, date, legacy_create_date, create_date FROM todo_task WHERE lead_id IS NULL LOOP
        -- Find user_id from allocated_to or default to 2 (Admin)
        SELECT id INTO uid_val FROM res_users WHERE login = r.allocated_to OR name = r.allocated_to LIMIT 1;
        IF uid_val IS NULL THEN
            uid_val := 2;
        END IF;

        -- Create a lead
        INSERT INTO crm_lead (
            name, contact_name, partner_name, user_id, type, active, create_date, priority, custom_lead_source
        ) VALUES (
            COALESCE(r.reference_name, r.name),
            COALESCE(r.reference_name, r.name),
            COALESCE(r.reference_name, r.name),
            uid_val,
            'opportunity',
            true,
            COALESCE(r.legacy_create_date, r.create_date, NOW()),
            '1',
            COALESCE(r.reference_type, 'To-Do Import')
        ) RETURNING id INTO new_lead_id;

        -- Update todo with this new lead
        UPDATE todo_task SET lead_id = new_lead_id WHERE id = r.id;
    END LOOP;
END $$;

-- 4. Final verification: check that 0 unlinked todos exist and 0 unlinked leads exist
SELECT count(*) as total_leads, count(CASE WHEN user_id IS NULL THEN 1 END) as leads_without_salesperson FROM crm_lead;
SELECT count(*) as total_todos, count(CASE WHEN lead_id IS NULL THEN 1 END) as todos_without_lead FROM todo_task;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
