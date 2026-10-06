import subprocess

sql = """
-- 1. Inspect unlinked todos
SELECT id, name, reference_type, reference_name, allocated_to 
FROM todo_task 
WHERE lead_id IS NULL 
LIMIT 20;

-- 2. Try linking unlinked todos by reference_name matching crm_lead.custom_naming_series or name or legacy_id
UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
WHERE t.lead_id IS NULL 
  AND (
    (t.reference_name IS NOT NULL AND t.reference_name != '' AND (t.reference_name = l.custom_naming_series OR t.reference_name = l.name))
    OR (t.name IS NOT NULL AND t.name = l.custom_naming_series)
  );

-- 3. Check how many remaining unlinked todos
SELECT count(*) as remaining_unlinked_todos 
FROM todo_task 
WHERE lead_id IS NULL;

-- 4. Check details of any remaining unlinked todos
SELECT id, name, reference_type, reference_name, allocated_to, description
FROM todo_task
WHERE lead_id IS NULL;
"""

cmd = (
    "sshpass -p 'Farai@#$1234' ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null root@127.0.0.1 "
    f"\"docker exec psql_showline_s2_havano_pro_xcynznxmwcotukbxkm psql -U Showline -d showline_s2_havano_pro_xcynznxmwcotukbxkm -c \\\"{sql}\\\"\""
)

res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
print("STDOUT:\n", res.stdout)
