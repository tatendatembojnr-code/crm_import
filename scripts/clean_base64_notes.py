import psycopg2
import re

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

print("Scanning for raw base64 strings in todo_task and mail_activity...")

# Find tasks where the name or description looks like raw base64 (e.g. starts with 6A/AC+ or long alphanumeric with /+)
cr.execute("""
    SELECT id, name, description 
    FROM todo_task 
    WHERE name ~ '^[A-Za-z0-9+/=]{40,}' 
       OR name LIKE '6A/AC+%'
       OR description LIKE '6A/AC+%';
""")
raw_tasks = cr.fetchall()
print(f"Found {len(raw_tasks)} tasks with raw base64 image strings.")

for tid, name, desc in raw_tasks:
    clean_subj = "Attachment / Image Note"
    cr.execute("UPDATE todo_task SET name = %s WHERE id = %s", (clean_subj, tid))
    cr.execute("UPDATE mail_activity SET summary = %s WHERE summary = %s OR note LIKE %s", (clean_subj, name, f"%{name[:30]}%"))

# Also sanitize mail_activity summaries
cr.execute("""
    UPDATE mail_activity 
    SET summary = 'Attachment / Image Note' 
    WHERE summary ~ '^[A-Za-z0-9+/=]{40,}' 
       OR summary LIKE '6A/AC+%';
""")

conn.commit()
print("✓ Successfully cleaned up all raw base64 / encrypted strings!")
