from odoo import models, fields, api


class CrmProduct(models.Model):
    _name        = 'crm.product'
    _description = 'CRM Product'
    _order       = 'sequence, name'

    name        = fields.Char(string='Product Name', required=True, translate=False)
    sequence    = fields.Integer(string='Sequence', default=10)
    active      = fields.Boolean(string='Active', default=True)
    description = fields.Text(string='Description')

    _sql_constraints = [
        ('name_uniq', 'unique(name)', 'A CRM product with this name already exists.'),
    ]

    @api.model
    def find_or_create(self, name):
        """Find an existing CRM product by name (case-insensitive) or create it."""
        if not name:
            return self.browse()
        name = str(name).strip()
        if not name:
            return self.browse()
        rec = self.search([('name', '=ilike', name)], limit=1)
        if rec:
            return rec
        return self.create({'name': name})
