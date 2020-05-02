# -*- coding: utf-8 -*-

from odoo import fields, models,tools,api,_

class ResComapny(models.Model):
    _inherit = 'res.company' 
    
    logout_time = fields.Integer(string='Logout Time(Sec.)',default="60")

