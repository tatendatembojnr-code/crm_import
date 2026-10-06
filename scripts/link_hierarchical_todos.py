import subprocess

sql = """
-- 1. Match ToDos pointing to other ToDos (reference_type = 'ToDo' or reference_name like 'T%')
UPDATE todo_task t
SET lead_id = parent.lead_id
FROM todo_task parent
WHERE t.lead_id IS NULL
  AND t.reference_name IS NOT NULL
  AND (t.reference_name = parent.name OR t.reference_name = parent.legacy_id)
  AND parent.lead_id IS NOT NULL;

-- 2. Match ToDos where reference_name matches crm_lead with pattern matching
UPDATE todo_task t
SET lead_id = l.id
FROM crm_lead l
WHERE t.lead_id IS NULL
  AND t.reference_name IS NOT NULL
  AND (
      t.reference_name = l.custom_naming_series
      OR t.reference_name = l.name
      OR l.custom_naming_series ILIKE '%' || t.reference_name || '%'
      OR t.reference_name ILIKE '%' || l.custom_naming_series || '%'
      OR (
          regexp_replace(t.reference_name, '[^0-9]', '', 'g') != ''
          AND regexp_replace(t.reference_name, '[^0-9]', '', 'g') = regexp_replace(l.custom_naming_series, '[^0-9]', '', 'g')
          AND length(regexp_replace(t.reference_name, '[^0-9]', '', 'g')) >= 4
      )
  );

-- 3. Check remaining unlinked todos
SELECT count(*) as unlinked_count FROM todo_task WHERE lead_id IS NULL;

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
