# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime, timedelta, date


class crm_lead(models.Model):
    _inherit = 'crm.lead'

    #budget_amount = fields.Float('')

    @api.model
    def create(self, vals):
        one = super(crm_lead, self).create(vals)
        budget = self.env['budget.budget'].create({
            'type': 'lead',
            'lead_id': one.id,
        })
        return one

    def compute_date_deadline(self):
        strptime = datetime.strptime
        strftime = datetime.strftime
        for one in self:
            project_date = one.project_date
            project_cycle = one.project_cycle
            if project_date and project_cycle:
                date_deadline = (strptime(project_date, DF) + project_cycle).strftime(DF)
            else:
                date_deadline = False
            one.date_deadline = date_deadline


    code_ref = fields.Char(u'项目编号')
    #相关客户用原生的partner_id，
    supplier_id = fields.Many2one('res.partner',u'相关供应商',domain=[('supplier', '=', True),('parent_id', '=', False)])
    project_date = fields.Date(u'立项日期')
    project_cycle = fields.Integer(u'立项周期')
    date_deadline = fields.Date('Expected Closing', compute=compute_date_deadline, help="Estimate of the date on which the opportunity will be won.")
    initiator_user_id = fields.Many2one('res.users',u'项目发起人')
    user_id = fields.Many2one('res.users', string='Salesperson', index=True, track_visibility='onchange', default=lambda self: self.env.user)
    product_manager_id = fields.Many2one('res.users',u'产品经理')
    @api.constrains('code_ref')
    def check_name(self):
        for one in self:
            if one.code_ref == False:
                break
            else:
                if self.search_count([('code_ref', '=', one.contract_suffix)]) > 1:
                    raise Warning('项目编号重复')