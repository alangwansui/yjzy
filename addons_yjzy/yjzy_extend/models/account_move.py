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
            new_advance_payment = i.new_advance_payment_id
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
                    'sslj_currency_id': sslj_currency_id.id,
                    'self_payment_id': self_payment_id.id}

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

    @api.depends('amount_currency', 'credit', 'credit', 'account_id', 'plan_invoice_id','move_id_state', 'new_advance_payment_id')
    def compute_sslj_balance(self):
        for one in self:
            amount_this_time = 0
            sslj_balance = 0
            sslj_invoice_balance = 0
            sslj_advance_balance = 0
            sslj_balance2 = 0.0
            amount_bank_cash_cny = 0.0
            amount_bank_cash_USD = 0.0
            # print('amount_currency_akiny',one.amount_currency)
            # if one.amount_currency > 0:
            #     amount_this_time = one.amount_currency
            # else:
            # print('polarity_akiny',one.account_id.polarity)
            if one.account_id.polarity in [1, -1]:
                if one.account_id.polarity == 1:
                    if one.amount_currency != 0:
                        amount_this_time = one.amount_currency
                    else:
                        amount_this_time = one.debit - one.credit
                    print('amount_this_time_akiny', amount_this_time)
                elif one.account_id.polarity == -1:
                    if one.amount_currency != 0:
                        amount_this_time = - one.amount_currency
                    else:
                        amount_this_time = one.credit - one.debit
                    print('amount_this_time_akiny', one.amount_currency, amount_this_time, one.credit, one.debit)
                # 'create_date', '<', one.create_date
                move_lines = None

                if one.account_id.code in ['1123', '2203']:
                    move_lines = one.env['account.move.line'].search(
                        [('move_id', '<', one.move_id.id), ('account_id', '=', one.account_id.id),
                         ('new_advance_payment_id', '!=', False),
                         ('new_advance_payment_id', '=', one.new_advance_payment_id.id),
                         ('move_id_state', '=', 'posted')])
                elif one.account_id.code in ['1122', '2202']:
                    move_lines = one.env['account.move.line'].search(
                        [('move_id', '<', one.move_id.id), ('account_id', '=', one.account_id.id),
                         ('invoice_id', '=', one.invoice_id.id), ('invoice_id', '!=', False),
                         ('move_id_state', '=', 'posted')])

                print('move_lines_akiny', move_lines, amount_this_time)
                if move_lines:
                    sslj_balance = sum(x.amount_this_time for x in move_lines) + amount_this_time
                else:
                    sslj_balance = amount_this_time
                one.amount_this_time = amount_this_time
                one.sslj_balance = sslj_balance

    @api.depends('amount_currency', 'account_id.user_type_id', 'debit', 'credit', 'account_id', 'new_payment_id',
                 'move_id_state', 'amount_this_time')
    def compute_amount_bank_cash(self):
        for one in self:
            if one.account_id.user_type_id.name == '银行和现金':
                if one.account_currency_id.name == 'CNY':
                    amount_bank_now = one.debit - one.credit
                else:
                    amount_bank_now = one.amount_currency
                one.amount_bank_now = amount_bank_now

            move_lines = self.env['account.move.line'].search(
                [('account_id', '=', one.account_id.id),('first_confirm_date', '<=', one.first_confirm_date),])



            aml_cny = self.env['account.move.line'].search(
                [('account_id.user_type_id.name', '=', '银行和现金'), ('account_id.currency_id.name', '=', 'CNY'),
                 ('first_confirm_date', '<=', one.first_confirm_date),
                 ('company_id','=',self.env.user.company_id.id)])

            aml_usd = self.env['account.move.line'].search(
                [('account_id.user_type_id.name', '=', '银行和现金'), ('account_id.currency_id.name', '=', 'USD'),
                 ('first_confirm_date', '<=', one.first_confirm_date),
                 ('company_id','=',self.env.user.company_id.id)])
            print('aml_cny_akiny',aml_cny,aml_usd)
            amount_bank_cash_cny = sum((x.debit - x.credit) for x in aml_cny)
            amount_bank_cash_USD = sum(x.amount_currency for x in aml_usd)
            sslj_balance2 = move_lines and sum(x.amount_bank_now for x in move_lines) or 0
            one.sslj_balance2 = sslj_balance2
            one.amount_bank_cash_cny = amount_bank_cash_cny
            one.amount_bank_cash_usd = amount_bank_cash_USD


    def _default_usd_currency_id(self):
        usd_currency_id = self.env['res.currency'].search([('name', '=', 'USD')])
        return usd_currency_id.id

    def _default_cny_currency_id(self):
        cny_currency_id = self.env['res.currency'].search([('name', '=', 'CNY')])
        return cny_currency_id.id

    @api.depends('amount_bank_now')
    def compute_is_pay_out_in(self):
        for one in self:
            if one.amount_bank_now > 0:
                one.is_pay_out_in = 'in'
            elif one.amount_bank_now < 0:
                one.is_pay_out_in = 'out'
            else:
                one.is_pay_out_in = 'zero'

    @api.depends('new_payment_id','create_date','new_payment_id.first_post_date')
    def compute_first_confirm_date(self):
        for one in self:
            new_payment_id = one.new_payment_id
            if new_payment_id:
                first_confirm_date = new_payment_id.first_post_date
            else:
                first_confirm_date = one.create_date
            one.first_confirm_date = first_confirm_date


    first_confirm_date = fields.Datetime('首次确认日期', compute=compute_first_confirm_date, store=True)#related='new_payment_id.first_post_date',
    is_pay_out_in = fields.Selection([('in','收款'),('out','付款'),('zero','零')],u'收付款类型',compute=compute_is_pay_out_in,store=True)

    comments = fields.Text('收付款备注')
    amount_bank_now = fields.Monetary('发生额2', currency_field='account_currency_id',compute='compute_amount_bank_cash',store=True)
    usd_currency_id = fields.Many2one('res.currency', '美金', default=lambda self: self._default_usd_currency_id())
    cny_currency_id = fields.Many2one('res.currency', '人名币', default=lambda self: self._default_cny_currency_id())
    account_currency_id = fields.Many2one('res.currency','科目币种',related='account_id.currency_id')
    amount_bank_cash_usd = fields.Monetary('公司总账余额(美金)',currency_field='usd_currency_id',compute='compute_amount_bank_cash', store=True)
    amount_bank_cash_cny = fields.Monetary('公司总账余额(人名币)',currency_field='cny_currency_id',compute='compute_amount_bank_cash',store=True)
    so_id = fields.Many2one('sale.order', u'销售订单')
    po_id = fields.Many2one('purchase.order', u'采购订单')

    plan_invoice_id = fields.Many2one('account.invoice', u'核销安排的发票')
    # yjzy_payment_id = fields.Many2one('yjzy.account.payment', u'新收付款')  #1106

    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告')
    expense_id = fields.Many2one('hr.expense', u'费用')
    move_id_state = fields.Selection([('draft', 'draft'), ('posted', 'posted')], 'Move State', related='move_id.state')

    hx_code = fields.Char(u'内部核对标记', related='expense_id.hx_code', store=True, index=True)

    new_payment_id = fields.Many2one('account.payment', u'收付款ID')
    new_advance_payment_id = fields.Many2one('account.payment', u'预收款单ID')

    gongsi_id = fields.Many2one('gongsi', '内部公司')

    sslj_currency_id = fields.Many2one('res.currency', compute=compute_sslj_currency_id)
    amount_this_time = fields.Monetary('发生金额', currency_field='sslj_currency_id', compute=compute_sslj_balance,
                                       store=True)
    sslj_balance = fields.Monetary('实时累计余额', currency_field='sslj_currency_id', compute=compute_sslj_balance,
                                   store=True)  # akiny计算分录日志
    sslj_balance2 = fields.Monetary('实时累计余额', currency_field='account_currency_id', compute='compute_amount_bank_cash',
                                   store=True)  # akiny计算分录日志
    self_payment_id = fields.Many2one('account.payment', u'对应的付款单')  # 所有申请单，付款单，收款单，都做一个记录。,用来对应sfk_type
    reconcile_type = fields.Selection([

        ('10_payment_out', u'付款支付'),
        ('20_advance_out', '预付认领'),
        ('30_payment_in', u'收款认领'),
        ('40_advance_in', u'预收认领'),
        ('50_reconcile', u'本次核销'),

    ], '认领方式', related='self_payment_id.reconcile_type')

    # @api.model
    # def create(self, vals):
    #     raise Exception('xxx')

    def open_new_payment_id(self):
        form_view = self.env.ref('yjzy_extend.view_fkzl_form')
        tree_view = self.env.ref('yjzy_extend.view_fkzl_tree')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'views': [(form_view.id, 'form')],
            'target': 'new',
            'res_id': self.new_payment_id.id,
            'flags': {'initial_mode': 'view', 'action_buttons': False,'headless':False},
            'context': {'is_open':1}
        }
    def open_new_payment_in_id(self):
        form_view = self.env.ref('yjzy_extend.view_rcskd_form_new')
        tree_view = self.env.ref('yjzy_extend.view_rcskd_tree_new_1')
        return {
            'type': 'ir.actions.act_window',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'views': [ (form_view.id, 'form')],
            'target': 'new',
            'res_id': self.new_payment_id.id,
            'flags': {'initial_mode': 'view', 'action_buttons': False,'headless':False},
            'context': {'is_open':1}
        }

    def compute_fkzl_rcskd_comments(self):
        for one in self:
            if one.new_payment_id.sfk_type in ['fkzl','rcskd']:
                one.comments = one.new_payment_id.payment_comments


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


# 重新统计后的明细
class account_move_line_com(models.Model):
    _name = 'account.move.line.com'

    @api.depends('self_payment_id', 'invoice_id', 'advance_payment_id')
    def compute_reconcile_type(self):
        for one in self:
            self_payment_id = one.self_payment_id
            invoice_id = one.invoice_id
            advance_payment_id = one.advance_payment_id
            account_id = one.account_id
            reconcile_type = ''
            if account_id.code in ['1122', '2202', '1123', '2203']:
                if self_payment_id:
                    if self_payment_id.reconcile_type:
                        reconcile_type = self_payment_id.reconcile_type
                    else:
                        if one.sslj_balance == self_payment_id.amount and account_id.code in ['1123', '2203']:
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

    partner_id = fields.Many2one('res.partner', '合作伙伴', related='move_id.partner_id')
    move_id = fields.Many2one('account.move', string='Journal Entry', ondelete="cascade",
                              help="The move of this entry line.", index=True, required=True, auto_join=True)
    company_id = fields.Many2one('res.company', '公司', related='move_id.company_id')

    account_id = fields.Many2one('account.account', string='Account', required=True, index=True,
                                 ondelete="cascade", domain=[('deprecated', '=', False)])
    sslj_currency_id = fields.Many2one('res.currency')
    amount_this_time = fields.Monetary('发生金额', currency_field='sslj_currency_id')
    sslj_balance = fields.Monetary('实时累计余额', currency_field='sslj_currency_id')  # akiny计算分录日志

    self_payment_id = fields.Many2one('account.payment', u'对应的付款单')
    reconcile_type = fields.Selection([
        ('03_advance_in', u'预收生成'),
        ('04_advance_out', u'预付生成'),
        ('05_invoice_in', u'应收账单生成'),
        ('07_invoice_out', u'应付账单生成'),
        ('10_payment_out', u'付款支付'),
        ('20_advance_out', '预付认领'),
        ('30_payment_in', u'收款认领'),
        ('40_advance_in', u'预收认领'),
        ('50_reconcile', u'本次核销'), ], '认领方式',
        compute=compute_reconcile_type)  # related='self_payment_id.reconcile_type'
    invoice_id = fields.Many2one('account.invoice')
    advance_payment_id = fields.Many2one('account.payment')

    move_date = fields.Date('日期', related='move_id.date')
