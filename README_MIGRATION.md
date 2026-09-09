# Odoo CRM & To-Do Migration Guide

This document outlines the exact steps and scripts used to migrate legacy ERPNext Leads and To-Dos into your Odoo CRM instance.

## 📁 Required Data Files
Before running any scripts, ensure your raw exported CSV files are located in:
`C:\Users\DELL\Desktop\odoo\data_import\`
1. **Leads**: `CRM Lead.csv`
2. **To-Dos**: `ToDo.csv`

## 🚀 How to Run the Migration (The Easy Way)
We have bundled the entire migration process into a single executable batch script.

1. Open your terminal or command prompt.
2. Navigate to the scripts directory:
   ```powershell
   cd C:\Users\DELL\Desktop\odoo\custom-addons\crm_extension\scripts
   ```
3. Run the master batch script:
   ```powershell
   .\run_all_migrations.bat
   ```
*(You can also just double-click `run_all_migrations.bat` from your Windows File Explorer!)*

---

## 🛠️ What the Scripts Do (Under the Hood)
If you need to run them manually or troubleshoot, here is the exact execution order:

### Step 1: Migrate Leads
**Script:** `fast_pg_import.py`
* Reads `CRM Lead.csv`
* Automatically formats legacy creation dates.
* Re-maps products to display clean Opportunity Titles.
* Injects leads directly into the PostgreSQL database (`crm.lead` table) for maximum performance.

### Step 2: Upload Raw To-Dos
**Script:** `upload_todos_right_away.py`
* Reads `ToDo.csv`
* Cleans up fractional seconds from timestamps (e.g., `14:30:00.890119` -> `14:30:00`).
* Directly creates raw `todo.task` records using the Odoo API.

### Step 3: Map To-Dos to Native Activities
**Script:** `convert_todos_to_activities.py`
* Reads all newly imported To-Dos.
* Cross-references the To-Do legacy IDs with the imported Leads' Emails and Phone numbers to find the correct match.
* Creates native **Odoo Activities** in the Activity Tab.
* If a To-Do was "Closed" or "Cancelled" in the legacy system, the script natively triggers `action_done()` so it moves beautifully into the chatter history without cluttering the active tasks view.

---
*Note: If you ever import more data, just place the new CSVs in the `data_import` folder and run the `.bat` file again!*
