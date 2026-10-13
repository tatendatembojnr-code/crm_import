{
    'name': 'CRM Live Intelligence & Overdue Tasks',
    'version': '1.8',
    'category': 'Sales/CRM',
    'summary': 'Live "Updated On" sorting, overdue activity auditing, product interest requirement & fast CSV import wizard.',
    'description': """
CRM Live Intelligence & Overdue Tasks
=====================================
* Live Updated Leads tracking across the company with accurate write_date/write_uid synchronization.
* Overdue and pending activity monitoring with automated auditing.
* Mandatory Product Interest field requirement for qualified lead intake.
* Hourly activity logs and chatter tracking.
* Fast CSV wizard to import Users, Leads, Opportunities, and To-Dos with deduplication.
    """,
    'author': 'DraftPOS / Havano Solutions',
    'website': 'https://draftpos.com',
    'license': 'LGPL-3',
    'depends': ['crm', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'data/crm_product_data.xml',
        'wizard/crm_import_wizard_views.xml',
        'views/crm_product_views.xml',
        'views/todo_task_views.xml',
        'views/crm_activity_log_views.xml',
        'views/crm_hourly_activity_log_views.xml',
        'views/crm_lead_views.xml',
        'views/mail_activity_schedule_views.xml',
    ],
    'assets': {
        'web.assets_backend': [
            'crm_import/static/src/views/**/*',
        ],
    },
    'images': ['static/description/icon.png'],
    'installable': True,
    'application': True,
}

