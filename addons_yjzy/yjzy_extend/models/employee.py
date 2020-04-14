# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    employee_sales_uid = fields.Many2one('hr.employee','费用对象')

    # def write(self, vals):
    #     if 'user_id' in vals:
    #         raise Warning('xxxxxxxxxxx')
    #     else:
    #         return super(hr_employee, self).write(vals)