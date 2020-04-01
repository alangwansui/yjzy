# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class hr_employee(models.Model):
    _inherit = 'hr.employee'

    # def write(self, vals):
    #     if 'user_id' in vals:
    #         raise Warning('xxxxxxxxxxx')
    #     else:
    #         return super(hr_employee, self).write(vals)