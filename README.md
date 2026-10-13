# CRM Live Activity & Overdue Intelligence (crm_import)

[![Odoo Version](https://img.shields.io/badge/Odoo-17.0%20%7C%2018.0-714B67?logo=odoo&logoColor=white)](https://www.odoo.com)
[![License: LGPL-3](https://img.shields.io/badge/License-LGPL--3-blue.svg)](LICENSE)
[![Category](https://img.shields.io/badge/Category-Sales%2FCRM-orange.svg)]()
[![Status](https://img.shields.io/badge/Status-Production%20Ready-brightgreen.svg)]()

> **Enterprise CRM Lead Intelligence, Live Updates Tracking, Overdue Activities Management & High-Speed Data Import Engine for Odoo.**

---

## 📌 Overview

**CRM Live Activity & Overdue Intelligence** upgrades Odoo's native CRM into a real-time sales execution powerhouse. Designed for high-volume sales teams, it provides immediate visibility into recently active leads across all representatives, monitors overdue tasks, enforces product interest requirements, and provides a robust CSV data importer for legacy migrations.

---

## ✨ Key Features

### 1. ⏱️ Real-Time "Updated On" Lead Intelligence
- **Global Activity Visibility**: Tracks the true `write_date` and `write_uid` across all interactions (notes, chatter, field edits, phone calls, and site visits).
- **Recent Update Prioritization**: Dedicated menu and smart filters to immediately surface leads that received updates today or this week.
- **Cross-Team Transparency**: Unlocks organizational-level visibility so sales managers and reps see updates across the company.

### 2. 🚨 Overdue & Pending Task Tracking
- **Automated Overdue Auditing**: Surfaces overdue activities and tasks before deals slip through the cracks.
- **Hourly Activity Logging**: Detailed logs tracking team activity distribution throughout the day.
- **Interactive To-Do Management**: Fast inline task updates, completions, and reschedules directly from the CRM workspace.

### 3. 🎯 Qualified Product Interest Tracking
- **Mandatory Product Interest**: Require sales reps to capture the customer's specific product or service interest during lead intake.
- **Product Interest Analytics**: Group, filter, and report on pipeline values segmented by product interest.

### 4. 🗂️ Clean, High-Productivity List & Form Views
- **Optimized Columns**: Contact phone numbers are visible by default, while secondary details (email, country, response status) are clean and toggleable (`optional="hide"`).
- **Tabbed Lead Form**: Clean notebook interface organizing contact information, deal metrics, and company details without redundant fields.

### 5. ⚡ Enterprise CSV Import Engine
- **Blazing Fast Ingestion**: Wizard-driven importer for Users, Leads, Opportunities, and To-Dos.
- **Duplicate Prevention**: Automatic deduplication matching phone, email, and company names to prevent clutter.
- **Data Integrity**: Preserves historical timestamps, notes, and salesperson assignments.

---

## 🚀 Installation & Setup

1. **Clone or Copy** this addon into your Odoo custom addons directory:
   ```bash
   git clone git@github.com:draftpos/crm_updated_on_overdue.git crm_import
   ```
2. **Update Addons List**:
   - Activate Developer Mode in Odoo (`Settings` -> `General Settings` -> `Activate Developer Mode`).
   - Navigate to `Apps` -> `Update Apps List`.
3. **Install the Module**:
   - Search for **CRM Live Activity & Overdue Intelligence** (`crm_import`).
   - Click **Install** or **Upgrade**.

---

## ⚙️ Configuration & Permissions

- **Sales Reps & Managers**: Seamlessly integrated into standard `Sales / User` and `Sales / Administrator` groups.
- **Custom Filters**: Includes pre-built filters for:
  - *Updated Today* (`write_date >= current_day`)
  - *Overdue Tasks* (`date_deadline < current_day`)
  - *My Updated Leads* vs *Team Updated Leads*

---

## 📁 Technical Information

| Attribute | Value |
|---|---|
| **Technical Name** | `crm_import` |
| **Category** | Sales/CRM |
| **Odoo Compatibility** | Odoo 17.0+ & Odoo 18.0+ |
| **Dependencies** | `crm`, `mail` |
| **License** | LGPL-3 |
| **Maintainer** | DraftPOS & Havano Solutions |

---

## 📄 License

This module is licensed under the **GNU Lesser General Public License v3.0 (LGPL-3)**. See the [LICENSE](LICENSE) file for details.
