import psycopg2

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

print("="*85)
print("=== AUDIT: ALL TODAY'S TASKS, ACTIVITIES, LEADS & ASSIGNED USERS ===")
print("="*85)

# 1. Check Today's CRM Activities in mail_activity
cr.execute("""
    SELECT 
        ma.id,
        ma.summary,
        ma.date_deadline,
        cl.id as lead_id,
        cl.name as lead_name,
        cl.custom_naming_series,
        ru.login as salesperson_login,
        rp.name as salesperson_name
    FROM mail_activity ma
    JOIN crm_lead cl ON ma.res_id = cl.id AND ma.res_model = 'crm.lead'
    LEFT JOIN res_users ru ON ma.user_id = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id
    WHERE ma.date_deadline = CURRENT_DATE
    ORDER BY ru.login ASC, cl.name ASC
""")
today_activities = cr.fetchall()

# 2. Check Today's Tasks in todo_task
cr.execute("""
    SELECT 
        tt.id,
        tt.legacy_id,
        tt.name as task_summary,
        tt.status,
        tt.allocated_to,
        tt.date as due_date,
        cl.id as lead_id,
        cl.name as lead_name,
        cl.custom_naming_series
    FROM todo_task tt
    LEFT JOIN crm_lead cl ON tt.lead_id = cl.id
    WHERE tt.date = CURRENT_DATE
    ORDER BY tt.allocated_to ASC
""")
today_todos = cr.fetchall()

# Breakdown by User for Today's Activities
user_act_counts = {}
for r in today_activities:
    user = r[7] or r[6] or 'Unassigned'
    user_act_counts[user] = user_act_counts.get(user, 0) + 1

# Breakdown by User for Today's To-Dos
user_todo_counts = {}
for r in today_todos:
    user = r[4] or 'Unassigned'
    user_todo_counts[user] = user_todo_counts.get(user, 0) + 1

print(f"\n1. TODAY'S CRM ACTIVITIES BREAKDOWN ({len(today_activities):,} Total Open Activities Due Today):")
for user, count in sorted(user_act_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  • {user:30s} : {count:,} activities due today")

print(f"\n2. TODAY'S TO-DOS IN todo_task ({len(today_todos):,} Total Tasks Due Today):")
for user, count in sorted(user_todo_counts.items(), key=lambda x: x[1], reverse=True):
    print(f"  • {user:30s} : {count:,} tasks due today")

print("\n3. SAMPLE 10 TODAY'S ACTIVITIES LINKED TO LEADS & SALESPEOPLE:")
for r in today_activities[:10]:
    act_id, summary, deadline, lead_id, lead_name, lead_series, user_login, user_name = r
    print(f"  Activity #{act_id}:")
    print(f"    - Salesperson: {user_name} ({user_login})")
    print(f"    - Lead:        [{lead_series or 'N/A'}] {lead_name[:40]}")
    print(f"    - Summary:     '{summary[:50]}'")
    print(f"    - Deadline:    {deadline}")

print("\n" + "="*85)
print("=== TODAY'S TASKS AUDIT COMPLETE ===")
print("="*85)
