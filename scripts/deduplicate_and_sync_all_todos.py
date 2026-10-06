import psycopg2
import psycopg2.extras
import html
import re
import time

print("="*85)
print("=== DEDUPLICATING AND SYNCHRONIZING ALL TO-DOS & ACTIVITIES ===")
print("="*85)

conn = psycopg2.connect(
    dbname='showline_s2_havano_pro_xcynznxmwcotukbxkm',
    user='Showline',
    password='Showline@#$1234',
    host='db',
    port=5432
)
cr = conn.cursor()

# Get crm.lead model id
cr.execute("SELECT id FROM ir_model WHERE model = 'crm.lead';")
crm_lead_model_id = cr.fetchone()[0]

# 1. Fetch user map: login -> (user_id, partner_id)
cr.execute("""
    SELECT lower(login), u.id, u.partner_id
    FROM res_users u
    WHERE login IS NOT NULL;
""")
user_map = {r[0]: (r[1], r[2]) for r in cr.fetchall()}
admin_user_id = user_map.get('admin', (2, 3))[0]
admin_partner_id = user_map.get('admin', (2, 3))[1]

# Pre-fetch lead salesperson map: lead_id -> (user_id, partner_id)
cr.execute("""
    SELECT cl.id, cl.name, cl.user_id, rp.id
    FROM crm_lead cl
    LEFT JOIN res_users ru ON cl.user_id = ru.id
    LEFT JOIN res_partner rp ON ru.partner_id = rp.id;
""")
lead_user_map = {}
for r in cr.fetchall():
    lid, lname, uid, pid = r[0], r[1], r[2], r[3]
    if uid and pid:
        lead_user_map[lid] = (uid, pid)
    else:
        lead_user_map[lid] = (admin_user_id, admin_partner_id)

# 2. Fetch distinct To-Dos by legacy_id to ensure 100% deduplication
print("Fetching all To-Dos from todo_task table...")
cr.execute("""
    SELECT DISTINCT ON (tt.legacy_id)
        tt.id,
        tt.legacy_id,
        tt.lead_id,
        tt.status,
        tt.allocated_to,
        tt.date,
        tt.name,
        tt.description,
        tt.create_date,
        tt.legacy_create_date
    FROM todo_task tt
    WHERE tt.lead_id IS NOT NULL AND tt.legacy_id IS NOT NULL
    ORDER BY tt.legacy_id, tt.id ASC;
""")
all_todos = cr.fetchall()
print(f"Total Unique To-Dos with valid Lead ID: {len(all_todos):,}")

open_todos = [t for t in all_todos if t[3] == 'Open']
closed_todos = [t for t in all_todos if t[3] == 'Closed']
print(f"  • Open To-Dos (for mail_activity):   {len(open_todos):,}")
print(f"  • Closed To-Dos (for mail_message):  {len(closed_todos):,}")

def clean_note_text(val):
    if not val:
        return ""
    s = str(val).strip()
    if 'data:image/' in s:
        s = re.sub(r'data:image/[a-zA-Z0-9+=/;,\-_]+', '', s)
    if '<' in s and '>' in s:
        return s
    return html.escape(s).replace('\n', '<br/>')

# 3. Clean and rebuild mail_activity for crm.lead
print("\nCleaning existing mail_activity on crm.lead...")
cr.execute("DELETE FROM mail_activity WHERE res_model = 'crm.lead';")
print(f"✓ Cleared old activities on crm.lead.")

print(f"Inserting {len(open_todos):,} clean Planned Activities into mail_activity...")
act_inserts = []
for t in open_todos:
    tid, leg_id, lead_id, status, alloc_to, due_date, summary, desc, cdate, leg_cdate = t
    alloc_key = (alloc_to or '').strip().lower()
    uid, pid = user_map.get(alloc_key, lead_user_map.get(lead_id, (admin_user_id, admin_partner_id)))
    
    ddate = due_date or (cdate.date() if cdate else None)
    if not ddate:
        ddate = time.strftime('%Y-%m-%d')
    
    clean_desc = clean_note_text(desc or summary)
    act_note = f"<p>{clean_desc}</p>" if clean_desc else None
    act_summary = (summary or 'To-Do')[:255]
    create_ts = leg_cdate or cdate or f"{ddate} 08:00:00"
    
    act_inserts.append((
        4,                  # activity_type_id (To-Do)
        'crm.lead',         # res_model
        lead_id,            # res_id
        crm_lead_model_id,  # res_model_id (872)
        act_summary,        # summary
        act_note,           # note
        ddate,              # date_deadline
        uid,                # user_id
        uid,                # create_uid
        uid,                # write_uid
        create_ts,          # create_date
        create_ts,          # write_date
        False               # automated
    ))

psycopg2.extras.execute_values(
    cr,
    """
    INSERT INTO mail_activity (
        activity_type_id, res_model, res_id, res_model_id,
        summary, note, date_deadline, user_id,
        create_uid, write_uid, create_date, write_date, automated
    ) VALUES %s
    """,
    act_inserts,
    page_size=3000
)
print(f"✓ Successfully inserted {len(act_inserts):,} unique Planned Activities!")

# 4. Clean duplicate To-Do done messages in mail_message and re-insert clean history
print("\nCleaning duplicate 'To-Do done' messages in mail_message...")
cr.execute("""
    DELETE FROM mail_message 
    WHERE model = 'crm.lead' AND body LIKE '%To-Do%done%';
""")
deleted_msgs = cr.rowcount
print(f"✓ Removed {deleted_msgs:,} duplicate To-Do done messages.")

print(f"Inserting {len(closed_todos):,} deduplicated Closed To-Do history messages into mail_message...")
msg_inserts = []
for t in closed_todos:
    tid, leg_id, lead_id, status, alloc_to, due_date, summary, desc, cdate, leg_cdate = t
    alloc_key = (alloc_to or '').strip().lower()
    uid, pid = user_map.get(alloc_key, lead_user_map.get(lead_id, (admin_user_id, admin_partner_id)))
    
    sum_txt = html.escape(str(summary or 'To-Do').strip())
    clean_desc = clean_note_text(desc)
    
    # Clean HTML body for To-Do done
    body = f"<div><p><span class='fa fa-check fa-fw'></span><span>To-Do</span> done <span>: </span><span>{sum_txt}</span></p><div><p>{clean_desc}</p></div></div>"
    
    create_ts = leg_cdate or cdate or (f"{due_date} 12:00:00" if due_date else "2026-07-01 12:00:00")
    
    msg_inserts.append((
        'crm.lead',     # model
        lead_id,        # res_id
        body,           # body
        'comment',      # message_type
        2,              # subtype_id (Note)
        pid,            # author_id
        create_ts,      # date
        uid,            # create_uid
        uid,            # write_uid
        create_ts,      # create_date
        create_ts,      # write_date
        True            # is_internal
    ))

psycopg2.extras.execute_values(
    cr,
    """
    INSERT INTO mail_message (
        model, res_id, body,
        message_type, subtype_id, author_id, date,
        create_uid, write_uid, create_date, write_date, is_internal
    ) VALUES %s
    """,
    msg_inserts,
    page_size=3000
)
print(f"✓ Successfully inserted {len(msg_inserts):,} unique To-Do completion messages into mail_message!")

# Commit all changes
conn.commit()
print("\n✓ Database Transaction Committed Successfully!")

# 5. Verify sample Lead014995 (BYD Steel Structures / 78626)
print("\n--- POST-DEDUPLICATION VERIFICATION FOR LEAD 78626 (BYD Steel Structures) ---")
cr.execute("""
    SELECT ma.id, ma.date_deadline, ru.login, ma.summary, ma.note
    FROM mail_activity ma
    LEFT JOIN res_users ru ON ma.user_id = ru.id
    WHERE ma.res_model = 'crm.lead' AND ma.res_id = 78626;
""")
lead_acts = cr.fetchall()
print(f"Planned Activities Count: {len(lead_acts)}")
for a in lead_acts:
    print(f"  • Activity ID: {a[0]} | Due: {a[1]} | User: {a[2]} | Summary: {a[3]}")

cr.execute("""
    SELECT mm.id, mm.date, rp.name, mm.body
    FROM mail_message mm
    LEFT JOIN res_partner rp ON mm.author_id = rp.id
    WHERE mm.model = 'crm.lead' AND mm.res_id = 78626 AND mm.body LIKE '%To-Do%done%'
    ORDER BY mm.date ASC;
""")
lead_msgs = cr.fetchall()
print(f"\nChatter Completed To-Dos Count: {len(lead_msgs)}")
for m in lead_msgs:
    print(f"  • Date: {m[1]} | Author: {m[2]} | Body: {m[3][:100]}")

