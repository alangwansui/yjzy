# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class account_move(models.Model):
    _inherit = 'account.move'

    reconcile_order_id = fields.Many2one('account.reconcile.order', u'核销单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    bill_id = fields.Many2one('transport.bill', u'发运单', related='invoice_id.bill_id')
    include_tax = fields.Boolean(u'含税', related='bill_id.include_tax')
    tb_contract_code = fields.Char(u'出运合同号', related='bill_id.ref')

    purchase_contract_code = fields.Char(u'采购合同号')

    gongsi_id = fields.Many2one('gongsi', '内部公司')



    @api.multi
    def post(self):
        res = super(account_move, self).post()
        return res

class account_move_line(models.Model):
    _inherit = 'account.move.line'

    def compute_sslj_currency_id(self):
        for one in self:
            if not one.sslj_currency_id:
                sslj_currency_id = self.env.user.company_id.currency_id
            else:
                sslj_currency_id = self.currency_id
            one.sslj_currency_id = sslj_currency_id



    @api.depends('amount_currency','credit','credit','account_id','plan_invoice_id','new_advance_payment_id')
    def compute_sslj_balance(self):
        for one in self:
            amount_this_time = 0
            sslj_balance = 0
            # print('amount_currency_akiny',one.amount_currency)
            # if one.amount_currency > 0:
            #     amount_this_time = one.amount_currency
            # else:
            # print('polarity_akiny',one.account_id.polarity)
            if one.account_id.polarity in [1,-1]:
                if one.account_id.polarity == 1:
                    if one.amount_currency != 0:
                        amount_this_time = one.amount_currency
                    else:
                        amount_this_time = one.debit - one.credit
                    print('amount_this_time_akiny',amount_this_time)
                elif one.account_id.polarity == -1:
                    if one.amount_currency != 0:
                        amount_this_time = - one.amount_currency
                    else:
                        amount_this_time = one.credit - one.debit
                    print('amount_this_time_akiny', one.amount_currency,amount_this_time,one.credit,one.debit)


                # date_time = one.create_date.strftime('%Y-%m-%d %H:%M:%S')


                move_lines = one.env['account.move.line'].search([('create_date','<',one.create_date),('account_id','=',one.account_id.id),
                                                                   '|','&',('invoice_id','=',one.invoice_id.id),('invoice_id','!=',False),
                                                                   '&',('new_advance_payment_id','!=',False),('new_advance_payment_id','=',one.new_advance_payment_id.id)])
                print('move_lines_akiny',move_lines,amount_this_time)

                sslj_balance = sum(x.amount_this_time for x in move_lines) + amount_this_time
            one.amount_this_time = amount_this_time
            one.sslj_balance = sslj_balance


    so_id = fields.Many2one('sale.order', u'销售订单')
    po_id = fields.Many2one('purchase.order', u'采购订单')

    plan_invoice_id = fields.Many2one('account.invoice', u'核销安排的发票')
    # yjzy_payment_id = fields.Many2one('yjzy.account.payment', u'新收付款')  #1106


    
    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告')
    expense_id = fields.Many2one('hr.expense', u'费用')

    hx_code = fields.Char(u'内部核对标记', related='expense_id.hx_code', store=True, index=True)

    new_payment_id = fields.Many2one('account.payment', u'收付款ID')
    new_advance_payment_id = fields.Many2one('account.payment', u'预收款单ID')

    gongsi_id = fields.Many2one('gongsi', '内部公司')

    sslj_currency_id = fields.Many2one('res.currency',compute=compute_sslj_currency_id)
    amount_this_time = fields.Monetary('发生金额',currency_field='sslj_currency_id',compute=compute_sslj_balance,store=True)
    sslj_balance = fields.Monetary('实时累计余额',currency_field='sslj_currency_id',compute=compute_sslj_balance,store=True) #akiny计算分录日志

    self_payment_id = fields.Many2one('account.payment',u'对应的付款单')#所有申请单，付款单，收款单，都做一个记录。,用来对应sfk_type
    reconcile_type = fields.Selection([

                                        ('10_payment_out', u'付款支付'),
                                       ('20_advance_out', '预付认领'),
                                       ('30_payment_in', u'收款认领'),
                                       ('40_advance_in', u'预收认领'),
                                       ('50_reconcile', u'本次核销'),

                                       ], '认领方式',related='self_payment_id.reconcile_type')

    # @api.model
    # def create(self, vals):
    #     raise Exception('xxx')






    def get_amount_to_currency(self, to_currency, date=False):
        self.ensure_one()
        ctx = {}
        date = date or self.date
        ctx.update({'date': date})
        if self.amount_currency:
            amount = self.currency_id.with_context(ctx).compute(self.amount_currency, to_currency)
        else:
            amount = self.company_currency_id.with_context(ctx).compute(self.debit - self.credit, to_currency)
        return amount







