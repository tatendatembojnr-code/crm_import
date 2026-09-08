import psycopg2
import time

def clean_duplicates():
    print("Connecting to PostgreSQL (showline_s2_havano_pro_xcynznxmwcotukbxkm at 192.168.112.2)...", flush=True)
    conn = psycopg2.connect(
        dbname="showline_s2_havano_pro_xcynznxmwcotukbxkm",
        user="Showline",
        password="Showline@#$1234",
        host="192.168.112.2",
        port=5432
    )
    conn.autocommit = True
    cur = conn.cursor()

    print("--- STEP 1: CLEANING DUPLICATE OPEN ACTIVITIES (mail_activity) ---", flush=True)
    cur.execute("""
        SELECT res_id, summary, array_agg(id ORDER BY id ASC)
        FROM mail_activity
        WHERE res_model = 'crm.lead' AND summary IS NOT NULL AND summary != ''
        GROUP BY res_id, summary
        HAVING count(*) > 1;
    """)
    duplicate_activities = cur.fetchall()
    print(f"Found {len(duplicate_activities):,} duplicate activity groups.", flush=True)

    activity_ids_to_delete = []
    for res_id, summary, ids in duplicate_activities:
        # Keep the first id, delete the rest
        activity_ids_to_delete.extend(ids[1:])

    if activity_ids_to_delete:
        print(f"Deleting {len(activity_ids_to_delete):,} duplicate mail_activity records...", flush=True)
        chunk_size = 1000
        for i in range(0, len(activity_ids_to_delete), chunk_size):
            chunk = tuple(activity_ids_to_delete[i:i + chunk_size])
            if len(chunk) == 1:
                cur.execute("DELETE FROM mail_activity WHERE id = %s;", (chunk[0],))
            else:
                cur.execute("DELETE FROM mail_activity WHERE id IN %s;", (chunk,))
        print("Finished deleting duplicate mail_activity records.", flush=True)
    else:
        print("No duplicate mail_activity records found.", flush=True)

    print("\n--- STEP 2: CLEANING DUPLICATE CHATTER MESSAGES (mail_message) ---", flush=True)
    cur.execute("""
        SELECT res_id, body, array_agg(id ORDER BY id ASC)
        FROM mail_message
        WHERE model = 'crm.lead' AND body LIKE '%To-Do%'
        GROUP BY res_id, body
        HAVING count(*) > 1;
    """)
    duplicate_messages = cur.fetchall()
    print(f"Found {len(duplicate_messages):,} duplicate chatter message groups.", flush=True)

    message_ids_to_delete = []
    for res_id, body, ids in duplicate_messages:
        # Keep the first id, delete the rest
        message_ids_to_delete.extend(ids[1:])

    if message_ids_to_delete:
        print(f"Deleting {len(message_ids_to_delete):,} duplicate mail_message records...", flush=True)
        chunk_size = 1000
        for i in range(0, len(message_ids_to_delete), chunk_size):
            chunk = tuple(message_ids_to_delete[i:i + chunk_size])
            if len(chunk) == 1:
                cur.execute("DELETE FROM mail_message WHERE id = %s;", (chunk[0],))
            else:
                cur.execute("DELETE FROM mail_message WHERE id IN %s;", (chunk,))
        print("Finished deleting duplicate mail_message records.", flush=True)
    else:
        print("No duplicate mail_message records found.", flush=True)

    cur.close()
    conn.close()
    print("\n=== DEDUPLICATION COMPLETE SUCCESSFULLY ===", flush=True)

if __name__ == '__main__':
    clean_duplicates()
