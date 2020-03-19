# -*- coding: utf-8 -*-

from odoo import models, fields, api

Budget_Type_Selection = [('employee', '员工预算'), ('company', '公司预算'), ('transport', '销售预算'), ('lead', '项目预算')]
Dic_Budget = dict(Budget_Type_Selection)


class budget_budget(models.Model):
    _name = 'budget.budget'
    _description = '预算'

    def compute_name(self):
        for one in self:
            name = ''
            ttype = one.type

            if ttype == 'employee':
                name = '%s:%s %s~%s' % (Dic_Budget[ttype], one.employee_id.name, one.date_start, one.date_end)
            elif ttype == 'company':
                name = '%s %s~%s' % (Dic_Budget[ttype], one.date_start, one.date_end)
            elif ttype == 'transport':
                name = '%s %s %s' % (Dic_Budget[ttype], one.tb_id.name)
            elif ttype == 'lead':
                name = '%s %s %s' % (Dic_Budget[ttype], one.lead_id.name)
            one.name = name

    def _get_default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    name = fields.Char('名称', compute=compute_name)
    state = fields.Selection([('draft', '草稿'), ('done', '完成')], '状态')
    active = fields.Boolean('有效', default=True)
    currency_id = fields.Many2one('res.currency', u'币种', default=_get_default_currency_id, required=True)

    amount_input = fields.Monetary('预算金额', currency_field='currency_id')
    type = fields.Selection(Budget_Type_Selection, u'预算类型', required=True)
    date_start = fields.Date('开始')
    date_end = fields.Date('结束')

    employee_id = fields.Many2one('hr.employee', '员工', required=False)
    tb_id = fields.Many2one('transport.bill', u'出运合同')
    lead_id = fields.Many2one('crm.lead', '项目')

    user_id = fields.Many2one('res.users', '用户', required=False)
    expense_ids = fields.One2many('hr.expense', 'budget_id', '费用明细')

    amount = fields.Monetary('预算金额', compute='compute_amount', currency_field='currency_id')
    amount_reset = fields.Monetary('剩余金额', compute='compute_amount', currency_field='currency_id')

    def compute_amount(self):
        for one in self:
            if one.type in ['employee', 'company']:
                amount = one.amount_input
            elif one.type in ['transport']:
                amount = one.tb_id.budget_amount
            elif one.type in ['lead']:
                pass

            one.amount = amount
            one.amount_reset = amount - sum(one.expense_ids.mapped('total_amount'))

    def get_budget(type, date):
        pass
