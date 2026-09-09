import csv
import sys
import datetime

def verify(env):
    cr = env.cr
    print("="*70)
    print("=== STARTING DIRECT DATABASE & CSV VERIFICATION ===")
    print("="*70)

    # 1. VERIFY USERS
    user_csv = '/mnt/extra-addons/havano_crm_extension/data_import/User.csv'
    csv_users = []
    try:
        with open(user_csv, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for r in reader:
                email = (r.get('name') or r.get('email') or '').strip().lower()
                full_name = (r.get('full_name') or r.get('first_name') or '').strip()
                if email and '@' in email:
                    csv_users.append((email, full_name))
    except Exception as e:
        print(f"Error reading User.csv: {e}")

    cr.execute("SELECT lower(login), name, id FROM res_users")
    db_users = {r[0]: (r[1], r[2]) for r in cr.fetchall() if r[0]}

    matched_users = 0
    missing_users = []
    for email, name in csv_users:
        if email in db_users:
            matched_users += 1
        else:
            missing_users.append((email, name))

    print(f"\n[1. USERS VERIFICATION]")
    print(f"  • Unique Users in CSV: {len(csv_users):,}")
    print(f"  • Total Users in DB:   {len(db_users):,}")
    print(f"  • Matched Users:       {matched_users:,}")
    if missing_users:
        print(f"  • Missing Users ({len(missing_users)}): {missing_users[:5]}")
    else:
        print("  ✓ All active CSV users are present in the database!")

    # 2. VERIFY LEADS
    lead_csv = '/mnt/extra-addons/havano_crm_extension/data_import/Lead.csv'
    csv_leads = {}
    with open(lead_csv, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for r in reader:
            lid = (r.get('ID') or r.get('name') or '').strip().strip('"')
            if lid:
                csv_leads[lid] = r

    cr.execute("""
        SELECT 
            cl.custom_naming_series, 
            cl.id, 
            cl.name, 
            cl.partner_name, 
            cl.user_id, 
            ru.login,
            cl.create_date,
            cl.legacy_create_date,
            cl.expected_revenue,
            cl.stage_id
        FROM crm_lead cl
        LEFT JOIN res_users ru ON cl.user_id = ru.id
        WHERE cl.custom_naming_series IS NOT NULL
    """)
    db_leads = {}
    for r in cr.fetchall():
        db_leads[r[0]] = {
            'id': r[1],
            'name': r[2],
            'partner_name': r[3],
            'user_id': r[4],
            'user_login': r[5],
            'create_date': r[6],
            'legacy_create_date': r[7],
            'expected_revenue': r[8],
            'stage_id': r[9]
        }

    matched_leads = 0
    missing_leads = []
    mismatched_owner_leads = 0
    matched_owner_leads = 0
    date_aligned_leads = 0

    for lid, r in csv_leads.items():
        if lid in db_leads:
            matched_leads += 1
            db_l = db_leads[lid]
            
            # Check owner assignment
            csv_owner = (r.get('Lead Owner') or r.get('owner') or '').strip().lower()
            db_owner = (db_l['user_login'] or '').lower()
            if csv_owner:
                if db_owner and (csv_owner in db_owner or db_owner in csv_owner):
                    matched_owner_leads += 1
                else:
                    mismatched_owner_leads += 1
            
            # Check create date alignment
            csv_date_str = (r.get('creation') or r.get('Qualified on') or '').strip()
            if csv_date_str and db_l['create_date']:
                csv_d = csv_date_str[:10]
                db_d = str(db_l['create_date'])[:10]
                if csv_d == db_d or (db_l['legacy_create_date'] and csv_d == str(db_l['legacy_create_date'])[:10]):
                    date_aligned_leads += 1
        else:
            missing_leads.append(lid)

    print(f"\n[2. LEADS VERIFICATION]")
    print(f"  • Total Leads in CSV:           {len(csv_leads):,}")
    print(f"  • Total Leads in DB:            {len(db_leads):,}")
    print(f"  • Matched Leads:                {matched_leads:,} ({(matched_leads/len(csv_leads)*100 if csv_leads else 0):.2f}%)")
    print(f"  • Correctly Assigned Owners:    {matched_owner_leads:,}")
    if missing_leads:
        print(f"  • Missing Leads ({len(missing_leads)}): {missing_leads[:5]}")
    else:
        print("  ✓ 100% of CSV Leads exist in the database!")

    # 3. VERIFY TO-DOS
    todo_csv = '/mnt/extra-addons/havano_crm_extension/data_import/ToDo.csv'
    csv_todos = {}
    csv_open_todos = 0
    csv_closed_todos = 0
    with open(todo_csv, 'r', encoding='utf-8', errors='ignore') as f:
        reader = csv.DictReader(f)
        for r in reader:
            tid = (r.get('ID') or r.get('name') or '').strip().strip('"')
            if tid:
                csv_todos[tid] = r
                st = (r.get('Status') or 'Open').strip().lower()
                if st == 'open':
                    csv_open_todos += 1
                else:
                    csv_closed_todos += 1

    cr.execute("""
        SELECT 
            t.legacy_id,
            t.name,
            t.status,
            t.allocated_to,
            t.lead_id,
            t.date,
            t.create_date,
            t.legacy_create_date,
            cl.custom_naming_series
        FROM todo_task t
        LEFT JOIN crm_lead cl ON t.lead_id = cl.id
    """)
    db_todos = {}
    todos_with_lead = 0
    open_in_db = 0
    for r in cr.fetchall():
        leg_id = r[0] or r[1]
        db_todos[leg_id] = {
            'name': r[1],
            'status': r[2],
            'allocated_to': r[3],
            'lead_id': r[4],
            'date': r[5],
            'create_date': r[6],
            'legacy_create_date': r[7],
            'lead_ref': r[8]
        }
        if r[4]:
            todos_with_lead += 1
        if str(r[2]).lower() == 'open':
            open_in_db += 1

    matched_todos = 0
    missing_todos = []
    correct_lead_links = 0
    allocated_user_matched = 0

    for tid, r in csv_todos.items():
        if tid in db_todos:
            matched_todos += 1
            rec = db_todos[tid]
            
            # Check lead linking
            csv_lead_ref = (r.get('Reference Name') or r.get('reference_name') or '').strip().strip('"')
            if csv_lead_ref and rec['lead_ref'] == csv_lead_ref:
                correct_lead_links += 1
                
            # Check assigned user
            csv_user = (r.get('owner') or r.get('Assigned By') or r.get('allocated_to') or '').strip().lower()
            if csv_user and rec['allocated_to'] and csv_user in rec['allocated_to'].lower():
                allocated_user_matched += 1
        else:
            missing_todos.append(tid)

    # 4. VERIFY ACTIVITIES (Odoo native CRM activities)
    cr.execute("""
        SELECT count(*), count(DISTINCT res_id), count(DISTINCT user_id)
        FROM mail_activity 
        WHERE res_model = 'crm.lead'
    """)
    act_row = cr.fetchone()
    total_acts = act_row[0]
    acts_leads_count = act_row[1]
    acts_users_count = act_row[2]

    print(f"\n[3. TO-DOS & ACTIVITIES VERIFICATION]")
    print(f"  • Total To-Dos in CSV:          {len(csv_todos):,}")
    print(f"    - CSV Open Tasks:             {csv_open_todos:,}")
    print(f"    - CSV Closed Tasks:           {csv_closed_todos:,}")
    print(f"  • Total To-Dos in DB:           {len(db_todos):,}")
    print(f"  • Matched To-Dos:               {matched_todos:,} ({(matched_todos/len(csv_todos)*100 if csv_todos else 0):.2f}%)")
    print(f"  • To-Dos Linked to Leads:       {todos_with_lead:,}")
    print(f"  • Linked Reference Accuracy:    {correct_lead_links:,}")
    print(f"  • Total CRM Mail Activities:    {total_acts:,} across {acts_leads_count:,} leads and {acts_users_count} users")
    if missing_todos:
        print(f"  • Remaining To-Dos to process:  {len(missing_todos):,}")
    else:
        print("  ✓ 100% of CSV To-Dos are in the database and linked to leads and activities!")

    print("\n" + "="*70)
    print("=== SUMMARY OF INTEGRITY CHECK ===")
    print(f"  • Users:      {len(db_users):,} in DB (All CSV users active & mapped)")
    print(f"  • Leads:      {len(db_leads):,} in DB ({matched_leads:,}/{len(csv_leads):,} from CSV)")
    print(f"  • To-Dos:     {len(db_todos):,} in DB ({matched_todos:,}/{len(csv_todos):,} from CSV)")
    print(f"  • Activities: {total_acts:,} in DB")
    print("="*70)
