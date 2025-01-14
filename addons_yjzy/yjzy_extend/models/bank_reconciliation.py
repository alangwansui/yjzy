# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning, UserError

class BankReconciliation(models.Model):
    _name = 'bank.reconciliation'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = '银行对账'


    def _default_account_bank_statemen_old(self):
        journal_bank_cash_ids = self.env['account.journal'].search([('type','in',['bank','cash'])])
        obj = self.env['account.bank.statement']
        account_bank_statement_ids = {}
        for one in journal_bank_cash_ids:
            account_bank_statement_id = obj.create({'journal_id': one.id,
                                                    })
            account_bank_statement_ids |= account_bank_statement_id
        return account_bank_statement_ids



    def _default_account_bank_statemen(self):
        res = []
        type_obj = self.env['account.journal']
        journal_bank_cash_ids = type_obj.search([('type','in',['bank','cash']),('company_id','=',self.env.user.company_id.id)])
        for one in journal_bank_cash_ids:
            res.append((0, 0, {
                'journal_id': one.id,
                'date':fields.datetime.now(),
                'company_id':one.company_id.id,
                'state':'open',


            }))

        return res or None

    def _default_usd_currency_id(self):
        usd_currency_id = self.env['res.currency'].search([('name','=','USD')])
        return usd_currency_id.id

    def _default_cny_currency_id(self):
        cny_currency_id = self.env['res.currency'].search([('name', '=', 'CNY')])
        return cny_currency_id.id

    @api.depends('account_bank_statement_ids','account_bank_statement_ids.amount_account_bank_cash_usd','account_bank_statement_ids.amount_account_bank_cash_usd')
    def compute_account_usd_cny(self):
        for one in self:
            amount_usd = sum(x.amount_account_bank_cash_usd for x in one.account_bank_statement_ids)
            amount_cny = sum(x.amount_account_bank_cash_cny for x in one.account_bank_statement_ids)
            one.amount_usd = amount_usd
            one.amount_cny = amount_cny
    @api.depends('account_bank_statement_ids','account_bank_statement_ids.amount_account_bank_cash')
    def compute_amount_all(self):
        for one in self:
            one.amount_all = sum(x.amount_account_bank_cash for x in one.account_bank_statement_ids)

    @api.depends('account_bank_statement_ids', 'account_bank_statement_ids.balance_start')
    def compute_amount_balance_start(self):
        for one in self:
            one.amount_balance_start = sum(x.balance_start for x in one.account_bank_statement_ids)

    @api.depends('amount_balance_start', 'amount_all')
    def compute_diff_amount(self):
        for one in self:
            one.diff_amount = one.amount_balance_start - one.amount_all


    state = fields.Selection([('draft',u'草稿'),('un_done','对不上'),('done','完成'),('refuse','拒绝')],u'状态',readonly=True, copy=False, index=True, track_visibility='onchange',default='draft',)
    name = fields.Char('编号')
    date = fields.Date('对账日期',default=lambda self:fields.date.today())
    done_uid = fields.Many2one('res.users','审批人')
    done_date = fields.Datetime('完成日期')
    description = fields.Char('description',track_visibility='onchange')
    usd_currency_id = fields.Many2one('res.currency','美金',default=lambda self:self._default_usd_currency_id())
    cny_currency_id = fields.Many2one('res.currency','人名币', default=lambda self:self._default_cny_currency_id())
    amount_usd = fields.Monetary('美金总余额', currency_field = 'usd_currency_id',compute=compute_account_usd_cny,store=True)
    amount_cny = fields.Monetary('人名币总余额',currency_field = 'cny_currency_id',compute=compute_account_usd_cny,store=True)
    amount_all = fields.Float('总账面余额',compute=compute_amount_all,store=True)
    amount_balance_start = fields.Float('总实际账户余额',compute=compute_amount_balance_start,store=True)
    company_id = fields.Many2one('res.company',u'公司',default=lambda self: self.env.user.company_id.id)
    account_bank_statement_ids = fields.One2many('account.bank.statement','bank_reconciliation_id', default=lambda self: self._default_account_bank_statemen(),)
    diff_amount = fields.Float(u'总差额',compute=compute_diff_amount, store=True)



    # _sql_constraints = [
    #     ('unique_date', 'unique(date)', '一天只能创建一次对账单'),
    # ]
    def action_done_old(self):
        for x in self.account_bank_statement_ids:
            if x.amount_account_bank_cash != x.balance_start:
                # raise Warning('账户%s金额未能对上，请检查' % (x.journal_id.name))
                self.state = 'un_done'
            else:
                x.state='confirm'
                self.state='done'

    def action_done(self):
        un_done_account_bank_statement_ids = self.account_bank_statement_ids.filtered(lambda x: x.amount_account_bank_cash !=x.balance_start)
        if len(un_done_account_bank_statement_ids) > 0:
            self.state = 'un_done'
            for x in self.account_bank_statement_ids:
                x.state = 'confirm'
        else:
            for x in self.account_bank_statement_ids:
                x.state = 'confirm'
            self.state = 'done'

    def action_refuse(self):
        for x in self.account_bank_statement_ids:
            x.state='open'
        self.state='draft'

    # def write(self, vals):
    #     res = super(BankReconciliation, self).write(vals)
    #     bank_reconciliation_id = self.env['bank.reconciliation'].search(['date','=',fields.Date.today().strftime('%Y-%m-%d')])
    #     print('bank_reconciliation_id_akiny',bank_reconciliation_id)
    #     if len(bank_reconciliation_id) != 0:
    #         raise Warning('一天只允许创建一个对账单')
    #     return res

    def unlink(self):
        for one in self:
            if one.state != 'draft':
                raise Warning(u'只有草稿状态的对账单才允许删除!')
        return super(BankReconciliation, self).unlink()

    @api.constrains('date')
    def check_date(self):
        for one in self:
            if self.search_count([('date', '=', one.date),('company_id','=',one.company_id.id)]) > 1:
                raise Warning('同一天只能创建一次对账单')