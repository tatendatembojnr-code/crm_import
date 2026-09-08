#!/bin/bash
# -----------------------------------------------------------------------------
# Havano CRM & To-Do Data Import Runner
# Run this script whenever you upload new CSV files to data_import/
# -----------------------------------------------------------------------------

echo "Copying latest files to container mount..."
sudo cp -r /opt/odoo-secure/addons-custom/havano_crm_extension/* /home/showline_s2_havano_pro_xcynznxmwcotukbxkm/custom-addons/havano_crm_extension/

echo "Starting CRM Lead & To-Do Data Import..."
sudo docker exec odoo_showline_s2_havano_pro_xcynznxmwcotukbxkm python3 -c "import odoo; from odoo import tools, api, sql_db; tools.config.parse_config(['-c', '/etc/odoo/odoo.conf', '-d', 'showline_s2_havano_pro_xcynznxmwcotukbxkm']); cr = sql_db.db_connect('showline_s2_havano_pro_xcynznxmwcotukbxkm').cursor(); env = api.Environment(cr, 2, {}); exec(open('/mnt/extra-addons/havano_crm_extension/scripts/import_leads_native.py').read())"
