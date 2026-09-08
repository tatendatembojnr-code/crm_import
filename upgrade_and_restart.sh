#!/bin/bash
set -e

echo "=== STEP 1: Syncing addons to container directory ==="
sudo cp -r /opt/odoo-secure/addons-custom/havano_crm_extension/* /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/havano_crm_extension/

echo "=== STEP 2: Relocating POS Licenses to Settings & Updating Summaries ==="
sudo docker exec odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm python3 /mnt/extra-addons/havano_crm_extension/scripts/relocate_pos_licenses_to_settings.py
sudo docker exec odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm python3 /mnt/extra-addons/havano_crm_extension/scripts/fix_activity_summaries_instant.py

echo "=== STEP 3: Restarting Odoo container ==="
sudo docker restart odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm

echo "=== SUCCESS: POS Licenses moved to Settings & Odoo updated! ==="
