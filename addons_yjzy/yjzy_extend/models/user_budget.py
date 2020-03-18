# -*- coding: utf-8 -*-

from odoo import models, fields, api


class company_budget(models.Model):
    _name = 'company.budget'
    _description = '公司年度预算'

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency', u'币种', default=_get_default_currency_id, required=True)
    year = fields.Char('年', required=True)
    amount = fields.Monetary('预算金额', currency_field='currency_id')
    expense_ids = fields.One2many('hr.expense', 'company_budget_id', '费用明细')
    amount_reset = fields.Monetary('剩余金额', compute='compute_amount_reset', currency_field='currency_id')

    date_start = fields.Date('开始')
    date_end = fields.Date('结束')

    def compute_amount_reset(self):
        for one in self:
            one.amount_reset = one.amount - sum(one.expense_ids.mapped('total_amount'))


class user_budget(models.Model):
    _name = 'user.budget'
    _description = '人员年度预算'

    @api.depends('user_id', 'year')
    def compute_name(self):
        for one in self:
            one.name = '%s-%s' % (one.employee_id.name, one.year)

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    currency_id = fields.Many2one('res.currency', u'币种', default=_get_default_currency_id, required=True)
    name = fields.Char('名称', compute='compute_name', store=True)
    employee_id = fields.Many2one('hr.employee', string='员工', required=True)
    user_id = fields.Many2one('res.users', '用户', required=True)
    year = fields.Char('年', required=True)
    amount = fields.Monetary('预算金额', currency_field='currency_id')
    expense_ids = fields.One2many('hr.expense', 'user_budget_id', '费用明细')
    amount_reset = fields.Monetary('剩余金额', compute='compute_amount_reset', currency_field='currency_id')
    date_start = fields.Date('开始')
    date_end = fields.Date('结束')


    def compute_amount_reset(self):
        for one in self:
            one.amount_reset = one.amount - sum(one.expense_ids.mapped('total_amount'))

