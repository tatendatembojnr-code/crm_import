from verify_sales_rep_and_creator import run_sql

print("1. Updating remaining CRM leads create_uid...")
run_sql("UPDATE crm_lead SET create_uid = COALESCE(user_id, 2) WHERE create_uid IS NULL;")

print("2. Updating To-Dos create_uid from res_users...")
run_sql("UPDATE todo_task t SET create_uid = ru.id FROM res_users ru WHERE t.create_uid IS NULL AND LOWER(t.allocated_to) = LOWER(ru.login);")

print("3. Updating To-Dos create_uid from linked crm_lead...")
run_sql("UPDATE todo_task t SET create_uid = COALESCE(cl.create_uid, cl.user_id, 2) FROM crm_lead cl WHERE t.create_uid IS NULL AND t.lead_id = cl.id;")

print("4. Updating any fallback to admin (2)...")
run_sql("UPDATE todo_task SET create_uid = 2 WHERE create_uid IS NULL;")

print("Done!")
