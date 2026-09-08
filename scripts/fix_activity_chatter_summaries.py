import psycopg2
import html
import re
import os
import sys

DB_NAME = os.getenv("ODOO_DB", "showline_s2_havano_pro_xcynznxmwcotukbxkm")
DB_USER = os.getenv("ODOO_DB_USER", "Showline")
DB_PASS = os.getenv("ODOO_DB_PASS", "Showline@#$1234")
DB_HOST = os.getenv("ODOO_DB_HOST", "192.168.112.2")
DB_PORT = os.getenv("ODOO_DB_PORT", "5432")

def clean_html(text):
    if not text:
        return ""
    clean = html.unescape(re.sub(r'<[^>]+>', ' ', str(text)))
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def fix_summaries():
    print(f"Connecting to database '{DB_NAME}' at {DB_HOST}:{DB_PORT}...", flush=True)
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASS,
            host=DB_HOST,
            port=DB_PORT
        )
    except Exception as e:
        print(f"Direct connection failed ({e}). If inside container or local socket, trying fallback...", flush=True)
        try:
            conn = psycopg2.connect(dbname=DB_NAME)
        except Exception as e2:
            print(f"Database connection error: {e2}", file=sys.stderr)
            return

    conn.autocommit = True
    cur = conn.cursor()

    # 1. Update mail_activity summary from note HTML content
    print("Fetching mail_activity records on CRM leads with notes...", flush=True)
    cur.execute("""
        SELECT id, summary, note 
        FROM mail_activity 
        WHERE res_model = 'crm.lead' AND note IS NOT NULL AND TRIM(note) != '';
    """)
    activities = cur.fetchall()
    print(f"Found {len(activities):,} activities to inspect.", flush=True)

    updated_acts = 0
    for act_id, summary, note in activities:
        clean_text = clean_html(note)
        if clean_text:
            # Check if summary is empty, a legacy ID (starts with T or hash), or we can replace it with actual text
            if not summary or summary.startswith('T') or summary.startswith('0') or len(summary) <= 12 or summary == 'To-Do':
                new_summary = clean_text[:200]
                cur.execute("UPDATE mail_activity SET summary = %s WHERE id = %s;", (new_summary, act_id))
                updated_acts += 1

    print(f"Successfully updated {updated_acts:,} mail_activity summaries to show readable chatter notes!", flush=True)

    # 2. Update mail_message chatter bodies for closed To-Dos
    print("Updating closed To-Do chatter message summaries...", flush=True)
    cur.execute("""
        SELECT id, body 
        FROM mail_message 
        WHERE model = 'crm.lead' AND body LIKE '%<span>To-Do</span> done%';
    """)
    messages = cur.fetchall()
    print(f"Found {len(messages):,} closed To-Do chatter messages to inspect.", flush=True)

    updated_msgs = 0
    for msg_id, body_html in messages:
        if body_html and '<span>To-Do</span> done' in body_html:
            inner_matches = re.findall(r'<div>(.*?)</div>', body_html, re.DOTALL)
            if len(inner_matches) > 1:
                desc_html = inner_matches[-1]
                clean_text = clean_html(desc_html)
                if clean_text:
                    new_body = re.sub(
                        r'(<span>To-Do</span> done <span>: </span><span>)[^<]*(</span>)',
                        r'\g<1>' + html.escape(clean_text[:200]) + r'\2',
                        body_html
                    )
                    cur.execute("UPDATE mail_message SET body = %s WHERE id = %s;", (new_body, msg_id))
                    updated_msgs += 1

    print(f"Successfully updated {updated_msgs:,} chatter messages!", flush=True)

    cur.close()
    conn.close()
    print("=== SUMMARY FIX COMPLETE ===", flush=True)

if __name__ == '__main__':
    fix_summaries()
