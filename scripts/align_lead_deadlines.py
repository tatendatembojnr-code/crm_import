import os
import sys
import psycopg2

DB_NAME = os.getenv("ODOO_DB", "showline_s2_havano_pro_xcynznxmwcotukbxkm")
DB_USER = os.getenv("ODOO_DB_USER", "Showline")
DB_PASS = os.getenv("ODOO_DB_PASS", "Showline@#$1234")
DB_HOST = os.getenv("ODOO_DB_HOST", "192.168.112.2")
DB_PORT = os.getenv("ODOO_DB_PORT", "5432")

def align_deadlines():
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
        print(f"Error connecting to database: {e}", file=sys.stderr)
        return

    conn.autocommit = True
    cur = conn.cursor()

    print("Aligning CRM Lead date_deadline with latest chatter date, activities, and To-Dos...", flush=True)
    update_query = """
        UPDATE crm_lead l
        SET date_deadline = sub.latest_date
        FROM (
            SELECT l.id AS lead_id,
                   GREATEST(
                       (SELECT MAX(m.date::date) FROM mail_message m WHERE m.model = 'crm.lead' AND m.res_id = l.id),
                       (SELECT MAX(COALESCE(a.date_deadline, a.create_date::date)) FROM mail_activity a WHERE a.res_model = 'crm.lead' AND a.res_id = l.id),
                       (SELECT MAX(COALESCE(t.date, t.legacy_create_date::date, t.create_date::date)) FROM todo_task t WHERE t.lead_id = l.id)
                   ) AS latest_date
            FROM crm_lead l
        ) sub
        WHERE l.id = sub.lead_id AND sub.latest_date IS NOT NULL;
    """

    cur.execute(update_query)
    print(f"Successfully aligned deadlines for {cur.rowcount:,} CRM Lead records!", flush=True)

    cur.close()
    conn.close()

if __name__ == '__main__':
    align_deadlines()
