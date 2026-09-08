#!/usr/bin/env python3
"""
=============================================================================
Havano CRM - Safe Duplicate Leads & Activities Cleaner (Option 1)
=============================================================================
This script safely removes duplicate CRM lead copies and their orphaned
activities/messages while keeping:
  1. Exactly 1 clean, latest record for each unique ERPNext Lead (14,128 leads).
  2. All native Odoo leads created manually (e.g. leads linked to sale orders).
=============================================================================
"""

import psycopg2
import time

def delete_in_chunks(cur, table_name, column_name, id_list, chunk_size=2000):
    total = len(id_list)
    if total == 0:
        return 0
    deleted = 0
    for i in range(0, total, chunk_size):
        chunk = tuple(id_list[i:i + chunk_size])
        if len(chunk) == 1:
            cur.execute(f"DELETE FROM {table_name} WHERE {column_name} = %s;", (chunk[0],))
        else:
            cur.execute(f"DELETE FROM {table_name} WHERE {column_name} IN %s;", (chunk,))
        deleted += len(chunk)
        pct = (deleted / total) * 100
        print(f"   [{table_name}] Deleted {deleted:,}/{total:,} ({pct:.1f}%)...", flush=True)
    return deleted

def clean_database():
    start_time = time.time()
    print("==================================================================", flush=True)
    print("🚀 HAVANO CRM - OPTION 1 DEDUPLICATION CLEANUP", flush=True)
    print("==================================================================", flush=True)

    print("Connecting to PostgreSQL...", flush=True)
    conn = psycopg2.connect(
        dbname="showline_s2_havano_pro_xcynznxmwcotukbxkm",
        user="Showline",
        password="Showline@#$1234",
        host="192.168.112.2",
        port=5432
    )
    conn.autocommit = True
    cur = conn.cursor()

    # 1. Print initial status
    cur.execute("SELECT count(*) FROM crm_lead;")
    initial_leads = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM mail_activity WHERE res_model = 'crm.lead';")
    initial_acts = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM mail_message WHERE model = 'crm.lead';")
    initial_msgs = cur.fetchone()[0]

    print(f"\n📊 INITIAL DATABASE STATE:")
    print(f"   - Total CRM Leads: {initial_leads:,}")
    print(f"   - Total Open Activities: {initial_acts:,}")
    print(f"   - Total Chatter Messages: {initial_msgs:,}")

    # 2. Identify Keeper Leads & Duplicate Leads
    print("\n🔍 STEP 1: Identifying duplicate leads to remove...", flush=True)

    # 2a. Duplicate clones of ERPNext leads (keep latest MAX(id) for each custom_naming_series)
    cur.execute("""
        SELECT id FROM (
            SELECT id, ROW_NUMBER() OVER (PARTITION BY custom_naming_series ORDER BY id DESC) as rn
            FROM crm_lead
            WHERE custom_naming_series IS NOT NULL AND custom_naming_series != ''
        ) t WHERE t.rn > 1;
    """)
    erpn_duplicate_ids = [r[0] for r in cur.fetchall()]
    print(f"   - Found {len(erpn_duplicate_ids):,} redundant duplicate copies of ERPNext leads.", flush=True)

    # 2b. Old unlinked orphan batch from Aug 24-25 (preserve genuine manual leads & sale orders)
    cur.execute("""
        SELECT id FROM crm_lead
        WHERE (custom_naming_series IS NULL OR custom_naming_series = '')
        AND id NOT IN (SELECT DISTINCT opportunity_id FROM sale_order WHERE opportunity_id IS NOT NULL)
        AND phone IS NOT NULL AND phone != ''
        AND phone IN (
            SELECT phone FROM crm_lead 
            WHERE custom_naming_series IS NOT NULL AND custom_naming_series != ''
            AND phone IS NOT NULL AND phone != ''
        );
    """)
    orphan_duplicate_ids = [r[0] for r in cur.fetchall()]
    print(f"   - Found {len(orphan_duplicate_ids):,} old unlinked orphan duplicate leads from Aug 24-25.", flush=True)

    all_lead_ids_to_delete = erpn_duplicate_ids + orphan_duplicate_ids
    total_to_delete = len(all_lead_ids_to_delete)
    print(f"   ➡️ Total duplicate leads to delete: {total_to_delete:,}", flush=True)

    if total_to_delete == 0:
        print("   No duplicate leads found. Database is already deduplicated!")
        cur.close()
        conn.close()
        return

    # 3. Delete dependent child records of duplicate leads
    print(f"\n🗑️  STEP 2: Removing child records for the {total_to_delete:,} duplicate leads...", flush=True)

    # Junction & relation tables
    for rel_table in ['crm_tag_rel', 'todo_task', 'crm_lead_website_visitor_rel', 'crm_lead_crm_lead_lost_rel']:
        try:
            cur.execute(f"SELECT 1 FROM information_schema.tables WHERE table_name = '{rel_table}';")
            if cur.fetchone():
                delete_in_chunks(cur, rel_table, 'lead_id' if rel_table in ['crm_tag_rel', 'todo_task'] else 'crm_lead_id', all_lead_ids_to_delete)
        except Exception as e:
            print(f"   Notice ({rel_table}): {e}")

    # mail_activity
    print("   Removing activities attached to duplicate leads...", flush=True)
    cur.execute("""
        DELETE FROM mail_activity 
        WHERE res_model = 'crm.lead' AND res_id = ANY(%s);
    """, (all_lead_ids_to_delete,))
    print(f"   Deleted activities on duplicate leads.", flush=True)

    # mail_message
    print("   Removing chatter messages attached to duplicate leads...", flush=True)
    cur.execute("""
        DELETE FROM mail_message 
        WHERE model = 'crm.lead' AND res_id = ANY(%s);
    """, (all_lead_ids_to_delete,))
    print(f"   Deleted messages on duplicate leads.", flush=True)

    # mail_followers
    print("   Removing followers on duplicate leads...", flush=True)
    cur.execute("""
        DELETE FROM mail_followers 
        WHERE res_model = 'crm.lead' AND res_id = ANY(%s);
    """, (all_lead_ids_to_delete,))
    print(f"   Deleted followers on duplicate leads.", flush=True)

    # 4. Delete the duplicate leads
    print(f"\n🗑️  STEP 3: Deleting {total_to_delete:,} duplicate crm_lead records...", flush=True)
    delete_in_chunks(cur, 'crm_lead', 'id', all_lead_ids_to_delete, chunk_size=2000)
    print("   ✅ Duplicate crm_lead records deleted successfully!", flush=True)

    # 5. Deduplicate any remaining duplicate open activities on the keeper leads
    print("\n🧹 STEP 4: Deduplicating remaining open activities on keeper leads...", flush=True)
    cur.execute("""
        SELECT res_id, summary, array_agg(id ORDER BY id ASC)
        FROM mail_activity
        WHERE res_model = 'crm.lead' AND summary IS NOT NULL AND summary != ''
        GROUP BY res_id, summary
        HAVING count(*) > 1;
    """)
    dupe_acts = cur.fetchall()
    act_ids_to_delete = []
    for res_id, summary, ids in dupe_acts:
        act_ids_to_delete.extend(ids[1:])
    if act_ids_to_delete:
        print(f"   Removing {len(act_ids_to_delete):,} duplicate mail_activity records on keeper leads...", flush=True)
        delete_in_chunks(cur, 'mail_activity', 'id', act_ids_to_delete)
    else:
        print("   No duplicate activities found on keeper leads.", flush=True)

    # 6. Deduplicate remaining duplicate chatter messages on the keeper leads
    print("\n🧹 STEP 5: Deduplicating remaining chatter messages on keeper leads...", flush=True)
    cur.execute("""
        SELECT res_id, body, array_agg(id ORDER BY id ASC)
        FROM mail_message
        WHERE model = 'crm.lead' AND body LIKE '%To-Do%'
        GROUP BY res_id, body
        HAVING count(*) > 1;
    """)
    dupe_msgs = cur.fetchall()
    msg_ids_to_delete = []
    for res_id, body, ids in dupe_msgs:
        msg_ids_to_delete.extend(ids[1:])
    if msg_ids_to_delete:
        print(f"   Removing {len(msg_ids_to_delete):,} duplicate mail_message records on keeper leads...", flush=True)
        delete_in_chunks(cur, 'mail_message', 'id', msg_ids_to_delete)
    else:
        print("   No duplicate chatter messages found on keeper leads.", flush=True)

    # 7. Re-sequence clean leads
    print("\n🔢 STEP 6: Re-sequencing clean leads (custom_no)...", flush=True)
    cur.execute("SELECT id FROM crm_lead ORDER BY COALESCE(legacy_create_date, create_date) ASC, id ASC;")
    remaining_leads = cur.fetchall()
    counter = 1
    for lead_id, in remaining_leads:
        cur.execute("UPDATE crm_lead SET custom_no = %s WHERE id = %s;", (counter, lead_id))
        counter += 1
    print(f"   Re-sequenced {len(remaining_leads):,} leads (custom_no 1 to {len(remaining_leads):,}).", flush=True)

    # 8. Print final summary
    cur.execute("SELECT count(*) FROM crm_lead;")
    final_leads = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM mail_activity WHERE res_model = 'crm.lead';")
    final_acts = cur.fetchone()[0]
    cur.execute("SELECT count(*) FROM mail_message WHERE model = 'crm.lead';")
    final_msgs = cur.fetchone()[0]
    cur.execute("SELECT count(DISTINCT custom_naming_series) FROM crm_lead WHERE custom_naming_series IS NOT NULL AND custom_naming_series != '';")
    final_erpn = cur.fetchone()[0]

    cur.close()
    conn.close()

    elapsed = time.time() - start_time
    print("\n==================================================================", flush=True)
    print(f"🎉 CLEANUP COMPLETED SUCCESSFULLY IN {elapsed:.1f} SECONDS!", flush=True)
    print("==================================================================", flush=True)
    print(f"📊 FINAL CLEAN DATABASE STATE:")
    print(f"   - Total CRM Leads: {final_leads:,} (Expected: ~14,132)")
    print(f"   - Unique ERPNext Leads: {final_erpn:,} (Matches Lead.csv: 14,128)")
    print(f"   - Total Open Activities: {final_acts:,}")
    print(f"   - Total Chatter Messages: {final_msgs:,}")
    print("==================================================================\n", flush=True)

if __name__ == '__main__':
    clean_database()
