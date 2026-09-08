import os
import sys

# Install paramiko if not present
try:
    import paramiko
except ImportError:
    print("Installing required library 'paramiko'...")
    os.system(f"{sys.executable} -m pip install paramiko")
    import paramiko

SERVER_IP = "173.249.39.201"
USERNAME = "fmakunya"
PASSWORD = r"Fortune@#$1234"
REMOTE_DIR = "/opt/odoo-secure/addons-custom/havano_crm_extension/data_import/"

files_to_upload = [
    r"C:\Users\DELL\Desktop\odoo\data_import\Lead.csv",
    r"C:\Users\DELL\Desktop\odoo\data_import\ToDo.csv"
]

print(f"Connecting to {USERNAME}@{SERVER_IP}...")
ssh = paramiko.SSHClient()
ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())

try:
    ssh.connect(SERVER_IP, port=22, username=USERNAME, password=PASSWORD)
    sftp = ssh.open_sftp()
    
    # Ensure remote directory exists
    try:
        sftp.mkdir(REMOTE_DIR)
    except IOError:
        pass  # Directory already exists
        
    for local_file in files_to_upload:
        filename = os.path.basename(local_file)
        remote_path = os.path.join(REMOTE_DIR, filename).replace('\\', '/')
        if os.path.exists(local_file):
            print(f"Uploading {filename} -> {remote_path} ...")
            sftp.put(local_file, remote_path)
            print(f"✓ {filename} uploaded successfully!")
        else:
            print(f"⚠ File not found locally: {local_file}")
            
    sftp.close()
    ssh.close()
    print("\nSUCCESS: All files transferred into CRM data_import folder on server!")

except Exception as e:
    print(f"\n❌ Error during transfer: {e}")
