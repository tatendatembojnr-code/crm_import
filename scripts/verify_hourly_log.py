import xmlrpc.client

url = "http://localhost:9060"
db = "showline_s2_havano_pro_xcynznxmwcotukbxkm"
common = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/common")
uid = common.authenticate(db, "admin", "Admin@Odoo1234!", {})
models = xmlrpc.client.ServerProxy(f"{url}/xmlrpc/2/object")

print("Checking crm.hourly.activity.log records via XML-RPC:")
try:
    records = models.execute_kw(
        db, uid, "Admin@Odoo1234!",
        "crm.hourly.activity.log", "search_read",
        [[]],
        {
            "fields": [
                "activity_date", "user_id",
                "h07_08", "h08_09", "h09_10", "h10_11", "h11_12", "h12_01",
                "h01_02", "h02_03", "h03_04", "h04_05", "h05_06",
                "total_count"
            ],
            "limit": 10
        }
    )
    print(f"Successfully fetched {len(records)} records!")
    for r in records:
        print(f"{r['activity_date']} | {r['user_id'][1] if r['user_id'] else 'None':<25} | 7-8: {r['h07_08']} | 8-9: {r['h08_09']} | 9-10: {r['h09_10']} | 10-11: {r['h10_11']} | 11-12: {r['h11_12']} | 12-1: {r['h12_01']} | 1-2: {r['h01_02']} | 2-3: {r['h02_03']} | 3-4: {r['h03_04']} | 4-5: {r['h04_05']} | 5-6: {r['h05_06']} | Total: {r['total_count']}")
except Exception as e:
    print("Error:", e)
