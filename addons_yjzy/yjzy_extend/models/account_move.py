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

    line_com_ids = fields.One2many('account.move.line.com', 'move_id', string='合并明细',
       copy=True)




    def create_account_move_line_com(self):
        move_obj = self.env['account.move.line.com']
        move_line_com_dic = {}
        self.line_com_ids = None
        for i in self.line_ids:
            account_id = i.account_id
            amount_this_time = i.amount_this_time
            sslj_balance = i.sslj_balance
            new_advance_payment= i.new_advance_payment_id
            sslj_currency_id = i.sslj_currency_id
            self_payment_id = i.self_payment_id
            partner_id = i.partner_id
            company_id = i.company_id
            if i.invoice_id:
                invoice_id = i.invoice_id
            else:
                invoice_id = i.plan_invoice_id
            move_id = i.move_id
            k = account_id.id
            if k in move_line_com_dic:
                print('k', k)
                move_line_com_dic[k]['amount_this_time'] += amount_this_time
                move_line_com_dic[k]['sslj_balance'] += sslj_balance

                if not move_line_com_dic[k]['advance_payment_id']:
                    move_line_com_dic[k]['advance_payment_id'] = new_advance_payment.id
                if not move_line_com_dic[k]['invoice_id']:
                    move_line_com_dic[k]['invoice_id'] = invoice_id.id
            else:
                print('k1', k)
                move_line_com_dic[k] = {
                    'account_id': account_id.id,
                    'advance_payment_id': new_advance_payment.id,
                    'amount_this_time': amount_this_time,
                    'sslj_balance': sslj_balance,
                    # 'partner_id':partner_id.id,

                    'invoice_id': invoice_id.id,
                    'sslj_currency_id':sslj_currency_id.id,
                    'self_payment_id':self_payment_id.id}

        for kk, data in list(move_line_com_dic.items()):
            line_com = move_obj.create({
                'move_id': self.id,
                'account_id': data['account_id'],
                'advance_payment_id': data['advance_payment_id'],
                'amount_this_time': data['amount_this_time'],

                # 'partner_id': data['partner_id'],
                'invoice_id': data['invoice_id'],
                'sslj_currency_id': data['sslj_currency_id'],
                'self_payment_id': data['self_payment_id'],
                'sslj_balance': data['sslj_balance'],

            })





    @api.multi
    def post(self):
        res = super(account_move, self).post()
        self.create_account_move_line_com()
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
            sslj_invoice_balance = 0
            sslj_advance_balance = 0
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




                #'create_date', '<', one.create_date
                if one.account_id.code in ['1123','2203']:

                    move_lines = one.env['account.move.line'].search([('move_id','<',one.move_id.id),('account_id','=',one.account_id.id),
                                                                   ('new_advance_payment_id','!=',False),
                                                                      ('new_advance_payment_id','=',one.new_advance_payment_id.id),('move_id_state','=','posted')])
                if one.account_id.code in ['1122','2202']:
                    move_lines = one.env['account.move.line'].search(
                        [('move_id', '<', one.move_id.id), ('account_id', '=', one.account_id.id),
                         ('invoice_id', '=', one.invoice_id.id), ('invoice_id', '!=', False),('move_id_state','=','posted')])

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
    move_id_state = fields.Selection([('draft','draft'),('posted','posted')],'Move State',related='move_id.state')

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

#重新统计后的明细
class account_move_line_com(models.Model):
    _name = 'account.move.line.com'

    @api.depends('self_payment_id','invoice_id','advance_payment_id')
    def compute_reconcile_type(self):
        for one in self:
            self_payment_id = one.self_payment_id
            invoice_id = one.invoice_id
            advance_payment_id = one.advance_payment_id
            account_id = one.account_id
            reconcile_type = ''
            if account_id.code in ['1122','2202','1123','2203']:
                if self_payment_id:
                    if self_payment_id.reconcile_type:
                        reconcile_type = self_payment_id.reconcile_type
                    else:
                        if one.sslj_balance == self_payment_id.amount and account_id.code in ['1123','2203']:
                            if account_id.code == '2203':
                                reconcile_type = '03_advance_in'
                            else:
                                reconcile_type = '04_advance_out'
                else:
                    if account_id.code in ['1122', '2202']:
                        if account_id.code == '1122':
                            reconcile_type = '05_invoice_in'
                        else:
                            reconcile_type = '07_invoice_out'
                #     invoice_id:
                #     if invoice_id.type == 'in_invoice':
                #         reconcile_type = '07_invoice_out'
                #     elif invoice_id.type == 'out_invoice':
                #         reconcile_type = '05_invoice_in'
                # elif advance_payment_id:
                #     if advance_payment_id.sfk_type == 'ysrld':
                #         reconcile_type = '03_advance_in'
                #     elif advance_payment_id.sfk_type == 'yfsqd':
                #         reconcile_type = '04_advance_out'
                one.reconcile_type = reconcile_type



    partner_id = fields.Many2one('res.partner','合作伙伴',related='move_id.partner_id')
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade",
                              help="The move of this entry line.", index=True, required=True, auto_join=True)
    company_id = fields.Many2one('res.company','公司',related='move_id.company_id')


    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
                                 ondelete="cascade", domain=[('deprecated', '=', False)])
    sslj_currency_id = fields.Many2one('res.currency')
    amount_this_time = fields.Monetary('发生金额',currency_field='sslj_currency_id')
    sslj_balance = fields.Monetary('实时累计余额',currency_field='sslj_currency_id') #akiny计算分录日志


    self_payment_id = fields.Many2one('account.payment', u'对应的付款单')
    reconcile_type = fields.Selection([
        ('03_advance_in',u'预收生成'),
        ('04_advance_out',u'预付生成'),
        ('05_invoice_in',u'应收账单生成'),
        ('07_invoice_out',u'应付账单生成'),
        ('10_payment_out', u'付款支付'),
        ('20_advance_out', '预付认领'),
        ('30_payment_in', u'收款认领'),
        ('40_advance_in', u'预收认领'),
        ('50_reconcile', u'本次核销'),], '认领方式',compute=compute_reconcile_type)#related='self_payment_id.reconcile_type'
    invoice_id = fields.Many2one('account.invoice')
    advance_payment_id = fields.Many2one('account.payment')

    move_date = fields.Date('日期',related='move_id.date')

