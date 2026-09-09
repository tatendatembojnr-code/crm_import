{
    'name': 'CRM Import',
    'version': '1.0',
    'category': 'Sales/CRM',
    'summary': 'Clean, fast UI Wizard to import Users, Leads, and To-Dos from CSV.',
    'description': """
        This module provides a UI wizard to import data from legacy systems.
        It defines custom fields to preserve data integrity and includes logic
        to skip existing records for speed.
    """,
    'depends': ['crm'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/crm_import_wizard_views.xml',
        'views/todo_task_views.xml',
        'views/crm_lead_views.xml',
    ],
    'installable': True,
    'application': False,
}
