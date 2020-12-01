# -*- encoding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

# Copyright (c) 2011 Noviat nv/sa (www.noviat.be). All rights reserved.

from odoo import fields, models


class AccountBankStatement(models.Model):
    _inherit = 'account.bank.statement'



    def compute_total(self):
        for one in self:
            amount_signed_payment_total = sum(x.amount_signed_payment for x in one.payment_ids)
            one.amount_signed_payment_total = amount_signed_payment_total

    def compute_balance(self):
        for one in self:
            aml_ids = self.env['account.move.line'].search(
                [('account_id', '=', self.journal_id.default_debit_account_id.id)])
            if one.currency_id.name == 'CNY':
                amount_account_bank_cash = sum([x.debit - x.credit  for x in aml_ids])
            else:
                amount_account_bank_cash = sum([x.amount_currency for x in aml_ids])
            one.amount_account_bank_cash = amount_account_bank_cash



    payment_ids = fields.Many2many('account.payment','bks_pay','payment_id','bks_id',u'今日付款单')
    amount_signed_payment_total = fields.Monetary(u'今日余额',currency_field='currency_id',compute=compute_total)
    amount_account_bank_cash = fields.Monetary(u'今日余额',currency_field='currency_id',compute=compute_balance)
    # amount_account_balance = fields.Monetary(u'总账余额',currency_field='currency_id',compute=compute_total)
    # 创建预付核销单从多个账单通过服务器动作创建 ok，

    def add_payment_ids(self):
        payment_ids = self.env['account.payment'].search([('state_1','in',['50_posted','60_done']),('journal_id','=',self.journal_id.id)],limit=100)
        self.payment_ids = payment_ids







