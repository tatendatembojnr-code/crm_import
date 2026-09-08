#!/usr/bin/env python3
"""
=============================================================================
Havano CRM - Remap Salespersons & Activities to Correct Users
=============================================================================
This script maps all leads in crm_lead to their rightful salesperson based on
the "Lead Owner" from Lead.csv and the User details from User.csv.
It also updates open activities (mail_activity) to belong to the assigned rep.
=============================================================================
"""

import csv
import psycopg2
import sys

def run_mapping():
    print("==================================================================", flush=True)
    print("🚀 HAVANO CRM - REMAPPING SALESPERSONS & ACTIVITIES", flush=True)
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

    # 1. Exact mapping from Lead Owner email / name to Odoo User ID
    owner_to_uid = {
        'mitchel@gmail.com': 18,
        'tafadzwa@showline.co.zw': 17,
        'stacey@maypack.co.zw': 596,
        'gerrylynn@showline.co.zw': 3731,
        'alson@showline.co.zw': 82796,
        'monica@showline.co.zw': 3737,
        'salessa@havano.co.zw': 3741,
        'chiedzagwature@gmail.com': 82788,
        'vimbai@showline.co.zw': 2396,
        'kupakwashe@showline.com': 3734,
        'kupakwashe@showline.co.zw': 3733,
        'support3@showline.co.zw': 3747,
        'support2@showline.co.zw': 3746,
        'support1@showline.co.zw': 3745,
        'admin@gmail.com': 3724,
        'admin@showline.co.zw': 3725,
        'admin2@showline.co.zw': 3726,
        'admire@showline.co.zw': 3727,
        'martketing@showline.co.zw': 3736,
        'support4@showline.co.zw': 82803,
        'sandra@showline.co.zw': 3742,
        'francis@showline.co.zw': 3730,
        'administrator': 2,
        'admin': 2
    }

    # 2. Update partner names so the UI badges display clean names from User.csv
    partner_names = {
        18: 'Mitchel Fish',
        17: 'Kundai Chitima',
        596: 'Sly',
        3731: 'Gerrylynn Gerrylynn',
        82796: 'Alson Musarurwa',
        3737: 'Monica',
        3741: 'Rose Mupandawana',
        82788: 'Chiedza Gwature',
        2396: 'Carrington Nyamukondiwa',
        3734: 'Kuppakwashe',
        3747: 'Munesu',
        3746: 'Tinashe Mu',
        3745: 'Tawedzerwa',
        3736: 'Tapfuma',
        82803: 'Alex Hwenha',
        3742: 'Sandra',
        3730: 'Francis1 Hwenha',
    }

    print("Updating Salesperson names in res_partner...", flush=True)
    for uid, full_name in partner_names.items():
        cur.execute("""
            UPDATE res_partner p
            SET name = %s
            FROM res_users u
            WHERE u.id = %s AND u.partner_id = p.id;
        """, (full_name, uid))

    # 3. Read Lead.csv to get Lead Owner for each Lead ID
    lead_csv = "/opt/odoo-secure/addons-custom/havano_crm_extension/data_import/Lead.csv"
    print(f"Reading Lead Owners from {lead_csv}...", flush=True)

    uid_to_leads = {}
    total_scanned = 0
    with open(lead_csv, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for r in reader:
            total_scanned += 1
            lid = (r.get("ID") or "").strip().strip('"')
            owner = (r.get("Lead Owner") or "").strip().lower()
            if lid and owner in owner_to_uid:
                uid = owner_to_uid[owner]
                uid_to_leads.setdefault(uid, []).append(lid)

    print(f"Scanned {total_scanned:,} rows. Mapped {sum(len(v) for v in uid_to_leads.values()):,} leads to their owners.", flush=True)

    # 4. Batch update crm_lead in database
    print("\nUpdating crm_lead.user_id in database...", flush=True)
    total_leads_updated = 0
    for uid, lids in uid_to_leads.items():
        chunk_size = 1000
        for i in range(0, len(lids), chunk_size):
            chunk = lids[i:i + chunk_size]
            cur.execute("""
                UPDATE crm_lead 
                SET user_id = %s 
                WHERE custom_naming_series = ANY(%s);
            """, (uid, chunk))
            total_leads_updated += cur.rowcount
            print(f"   [User ID {uid}] Updated {total_leads_updated:,} leads so far...", flush=True)

    print(f"\n✅ Total leads updated with rightful salesperson: {total_leads_updated:,}")

    # 5. Update open activities (mail_activity) so they are assigned to the lead owner
    print("\nSyncing open activities (mail_activity) to assigned salespersons...", flush=True)
    cur.execute("""
        UPDATE mail_activity a
        SET user_id = l.user_id
        FROM crm_lead l
        WHERE a.res_model = 'crm.lead' AND a.res_id = l.id AND l.user_id IS NOT NULL;
    """)
    print(f"✅ Synced {cur.rowcount:,} activities to match lead salesperson.", flush=True)

    # 6. Print final breakdown
    print("\n==================================================================", flush=True)
    print("📊 FINAL SALESPERSON DISTRIBUTION IN CRM", flush=True)
    print("==================================================================", flush=True)
    cur.execute("""
        SELECT u.id, p.name, u.login, count(l.id)
        FROM crm_lead l
        LEFT JOIN res_users u ON l.user_id = u.id
        LEFT JOIN res_partner p ON u.partner_id = p.id
        GROUP BY u.id, p.name, u.login
        ORDER BY count(l.id) DESC;
    """)
    for row in cur.fetchall():
        uid, name, login, cnt = row
        print(f"   👤 {name:<24} ({login:<28}) -> {cnt:>6,} leads")
    print("==================================================================", flush=True)
    print("🎉 ALL LEADS AND ACTIVITIES REMAPPED SUCCESSFULLY!", flush=True)

if __name__ == '__main__':
    run_mapping()
