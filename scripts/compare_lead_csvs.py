import csv
import os

for path in ['/tmp/gdrive_verify_2/file_b.csv', '/mnt/extra-addons/havano_crm_extension/data_import/Lead.csv']:
    if os.path.exists(path):
        size = os.path.getsize(path)
        print(f"File: {path} (size: {size:,} bytes)")
