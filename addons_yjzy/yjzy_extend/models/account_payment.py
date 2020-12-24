# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type

Option_Add = [
    ('advance', u'预收付'),
    ('date_after_ship', u'客户交单后的天数'),
    ('date_after_finish', u'供应商交单日期'),
]


class AccountPaymentTerm(models.Model):
    _inherit = "account.payment.term"
    #_order = "sequence"

    type = fields.Selection([('purchase', '采购'), ('sale', '销售'), ('comm', u'通用')], u'类型', default='comm')
    invoice_date_deadline_field = fields.Selection([('date_ship', u'出运船日期'), ('date_finish', '交单日期')])
    active = fields.Boolean(u'归档', default=True)

    #sequence = fields.Integer(u'排序', default=10, index=True)

    def get_advance(self, amount):
        self.ensure_one()
        advance = 0.0
        for line in self.line_ids:
            amt = 0
            if line.option == 'advance':
                amt = 0
                if line.value == 'fixed':
                    amt = line.value_amount
                elif line.value == 'percent':
                    amt = amount * (line.value_amount / 100.0)
                advance += amt
        return advance


class account_payment_term_line(models.Model):
    _inherit = 'account.payment.term.line'

    option = fields.Selection(selection_add=Option_Add)


class account_payment(models.Model):
    _inherit = 'account.payment'

    @api.one
    @api.depends('payment_ids')
    def compute_count(self):
        for one in self:
            self.ysrld_ids = self.payment_ids.filtered(lambda x: x.sfk_type == 'ysrld')
            self.yfsqd_ids = self.payment_ids.filtered(lambda x: x.sfk_type == 'yfsqd')
            advance_reconcile_order_count = len(self.advance_reconcile_order_line_ids.filtered(lambda x: x.amount_advance_org > 0 and x.order_id.state == 'done'))
            one.advance_reconcile_order_count = advance_reconcile_order_count
            one.count_ysrld = len(self.ysrld_ids)
            one.count_yfsqd = len(self.yfsqd_ids)
            one.count_yshx = len(self.yshx_ids)
            # one.count_ptskrl = len(self.ptskrl_ids)
            one.count_fybg = len(self.fybg_ids)


    def _compute_balance____(self):
        line_obj = self.env['account.move.line']
        for one in self:
            balance = 0
            if one.sfk_type == 'rcskd':
                lines = line_obj.search([('new_payment_id', '=', one.id), ('account_id.code', '=', '220301')])
                if one.currency_id.name == 'CNY':
                    balance = sum([x.credit - x.debit for x in lines])
                else:
                    balance = sum([-1 * x.amount_currency for x in lines])
            if one.sfk_type == 'rcfkd':
                lines = line_obj.search([('new_payment_id', '=', one.id), ('account_id.code', '=', '112301')])
                if one.currency_id.name == 'CNY':
                    balance = sum([x.debit - x.credit for x in lines])
                else:
                    balance = sum([x.amount_currency for x in lines])

            one.balance = balance


    @api.depends('aml_ids','state','ysrld_ids','ysrld_ids.state')
    def compute_balance(self):
        for one in self:
            balance = 0
            all_lines = one.aml_ids
            if one.sfk_type == 'rcskd':
                lines = all_lines.filtered(lambda x: x.account_id.code == '220301')
                if one.currency_id.name == 'CNY':
                    balance = sum([x.credit - x.debit for x in lines])
                else:
                    balance = sum([-1 * x.amount_currency for x in lines])

            if one.sfk_type == 'rcfkd':
                lines = all_lines.filtered(lambda x: x.account_id.code == '112301')
                if one.currency_id.name == 'CNY':
                    balance = sum([x.debit - x.credit for x in lines])
                else:
                    balance = sum([x.amount_currency for x in lines])
            if one.sfk_type == 'fkzl':
                lines = all_lines.filtered(lambda x: x.account_id.code == '112301')
                if one.currency_id.name == 'CNY':
                    balance = sum([x.debit - x.credit for x in lines])
                else:
                    balance = sum([x.amount_currency for x in lines])
            one.balance = balance
            if balance == 0 and one.state_1 == '50_posted':
                one.state_1 = '60_done'


            # if balance == 0 and one.x_wkf_state == '159':
            #     one.x_wkf_state = '163'
            #     one.state_1 = '60_done'
            #     one.test_reconcile()
            #     one.write({'state': 'reconciled'})
            # elif balance == 0 and one.state_1 == '50_posted':#参考核销
            #     one.state_1 = '60_done'
            #     one.test_reconcile()
            #     one.write({'state': 'reconciled'})
            #     print('compute_balance_1111111',one.state_1)
            #     # elif balance !=0 and one.x_wkf_state == '163':
            #     #  one.x_wkf_state = '159'
            # else:
            #     pass




    def _default_name(self):
        sfk_type = self.env.context.get('default_sfk_type')
        if sfk_type:
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        else:
            name = None
        return name


    @api.model
    def default_get(self, fields):
        ctx = self.env.context
        res = super(account_payment, self).default_get(fields)
        print('==========dg======', ctx)
        if ctx.get('default_sfk_type') == 'jiehui':
            res.update({
                'partner_id': self.env['res.partner'].search([('name','=','未定义')], limit=1).id
            })
        if ctx.get('default_sfk_type') == 'rcskd':
            res.update({
                'partner_id': self.env['res.partner'].search([('name','=','未定义')], limit=1).id
            })


        if ctx.get('active_model', '') == 'account.invoice':
            invoice = self.env['account.invoice'].browse(ctx.get('active_id'))
            if invoice.gongsi_id:
                res.update({'gongsi_id': invoice.gongsi_id.id})

        return res

    # @api.multi
    # def write(self, vals):
    #     res = super(account_payment, self).write(vals)
    #     self.compute_advance_type()
    #     return res

    @api.depends('advance_reconcile_order_line_ids.order_id.state','amount','advance_reconcile_order_line_ids.amount_advance_org',
                 'advance_reconcile_order_line_ids.yjzy_payment_id')
    def compute_advance_balance_total(self):
        for one in self:
            advance_total = sum([x.amount_advance_org for x in one.advance_reconcile_order_line_ids])
            advance_balance_total = one.amount - advance_total
            if advance_balance_total == 0 and one.state_1 == '50_posted':
                one.state_1 = '60_done'
                one.test_reconcile()
                one.write({'state': 'reconciled'})
            one.advance_total = advance_total
            one.advance_balance_total = advance_balance_total

    #针对收款单的查询
    @api.depends('yshx_ids','yshx_ids.state','aml_ids','yshx_ids.amount_advance_org','ysrld_ids','ysrld_ids.state','ysrld_ids.state','ysrld_ids.amount','ysrld_ids.advance_total','ysrld_ids.advance_balance_total','fybg_ids.state')
    def compute_rcskd_amount_total(self):
        for one in self:
            yshx_ids = one.yshx_ids.filtered(lambda x: x.state in ['posted','reconciled'])
            ysrld_ids = one.ysrld_ids.filtered(lambda x: x.state in ['posted','reconciled'])
            yshxd_amount_payment_org_total = sum(x.amount_advance_org for x in yshx_ids)
            ysrld_amount_total = sum(x.amount for x in ysrld_ids)
            ysrld_amount_advance_total = sum(x.advance_total for x in ysrld_ids)
            ysrld_amount_advance_balance_total = sum(x.advance_balance_total for x in ysrld_ids)
            one.yshxd_amount_payment_org_total = yshxd_amount_payment_org_total
            one.ysrld_amount_total = ysrld_amount_total
            one.ysrld_amount_advance_total = ysrld_amount_advance_total
            one.ysrld_amount_advance_balance_total = ysrld_amount_advance_balance_total
   #计算一个新的客户信息，当有预收或者应收认领的时候，打上对应的客户信息
    def _compute_partner_confirm_id(self):
        for one in self:
            ysrld_ids = one.ysrld_ids
            yshx_ids = one.yshx_ids
            partner_confirm_id = one.partner_id
            if ysrld_ids:
                partner_confirm_id = ysrld_ids[0].partner_id
            elif yshx_ids:
                partner_confirm_id = yshx_ids[0].partner_id
            one.partner_confirm_id = partner_confirm_id

    @api.depends('name', 'amount')
    def compute_display_name(self):
        ctx = self.env.context
        res = []
        for one in self:
            if ctx.get('default_sfk_type', '') == 'ysrld' or one.sfk_type == 'ysrld':
                if ctx.get('only_number'):
                    name='%s' % (str(one.advance_balance_total))
                else:
                    name = '%s:%s' % ('预收认领单', str(one.advance_balance_total))
            elif ctx.get('default_sfk_type', '') == 'fkzl' or one.sfk_type == 'fkzl':
                name = '%s:%s' % ('付款指令', one.name)
            elif ctx.get('default_sfk_type', '') == 'rcskd' or one.sfk_type == 'rcskd':
                name = '%s:%s' % ('日常收款单', one.balance)
            elif ctx.get('default_sfk_type', '') == 'yfsqd' or one.sfk_type == 'yfsqd':
                if ctx.get('advance_balance_total'):
                    name = '%s:%s' % (one.name, str(one.advance_balance_total))
                else:
                    name = '%s:%s' % ('预付申请', one.name)
            elif ctx.get('default_sfk_type', '') == 'nbzz' or one.sfk_type == 'nbzz':
                name = '%s:%s' % ('内部转账', one.name)

            elif ctx.get('default_sfk_type', '') == 'jiehui' or one.sfk_type == 'jiehui':
                name = '%s:%s' % ('结汇', one.name)

            elif ctx.get('bank_amount'):
                name = '%s[%s]' % (one.journal_id.name, str(one.balance))
            elif ctx.get('advance_bank_amount'):
                name = '%s[%s]' % (one.yjzy_payment_id.journal_id.name, str(one.advance_balance_total))
            elif ctx.get('fk_journal_id'):
                name = '%s[%s]' % (one.fk_journal_id.name, str(one.advance_balance_total))
            elif ctx.get('advance_so_amount'):
                if not one.yjzy_payment_id:
                    name = '%s[%s]' % (one.journal_id.name, str(one.balance))
                else:
                    if one.so_id:
                        name = '%s[%s]' % (one.so_id.contract_code, str(one.advance_balance_total))
                    else:
                        name= '%s[%s]' % ('无销售合同', str(one.advance_balance_total))
            elif ctx.get('advance_po_amount'):
                if not one.yjzy_payment_id:
                    name = '%s[%s]' % (one.journal_id.name, str(one.amount))
                else:
                    if one.po_id:
                        name = '%s[%s]' % (one.po_id.contract_code, str(one.advance_balance_total))
                    else:
                        name= '%s[%s]' % ('无采购合同', str(one.advance_balance_total))


            else:
                name = '%s[%s]' % (one.name, str(one.balance))
            print('ctx_1111',ctx)
            one.display_name = name

    def _compute_advance_reconcile_order_count_all(self):
        for one in self:
            print('teee', len(one.advance_reconcile_order_ids))
            advance_reconcile_order_count_all = len(one.advance_reconcile_order_ids)
            advance_reconcile_order_draft_ids_count = len(one.advance_reconcile_order_draft_ids)
            advance_reconcile_order_no_draft_ids_count = len(one.advance_reconcile_order_no_draft_ids)
            advance_reconcile_order_draft_amount_advance = sum(x.amount_advance_org for x in one.advance_reconcile_order_draft_ids)
            one.advance_reconcile_order_count_all = advance_reconcile_order_count_all
            one.advance_reconcile_order_draft_ids_count = advance_reconcile_order_draft_ids_count
            one.advance_reconcile_order_no_draft_ids_count = advance_reconcile_order_no_draft_ids_count
            one.advance_reconcile_order_draft_amount_advance = advance_reconcile_order_draft_amount_advance
            one.advance_reconcile_order_count_char = '%s/%s' % (str(advance_reconcile_order_draft_ids_count), str(advance_reconcile_order_count_all))
            one.advance_reconcile_order_no_draft_count_char = '%s/%s' % (
            str(advance_reconcile_order_draft_ids_count), str(advance_reconcile_order_no_draft_ids_count))

    @api.depends('po_id','so_id','partner_id','state','state_1')
    def compute_advance_type(self):
        for one in self:
            if one.po_id or one.so_id:
                one.advance_type = '20_contract'
            else:
                one.advance_type = '10_no_contract'

    @api.depends('yjzy_partner_id')
    def compute_invoice_advance(self):
        for one in self:
    #         if one.yjzy_partner_id:
    #             sale_normal_invoice_ids = self.env['account.invoice'].search(
    #                 [('residual', '>', 0), ('state', '=', 'open'), ('yjzy_type', '=', 'sale'), ('type', '=', 'out_invoice'),
    #                  ('partner_id', '=', one.yjzy_partner_id.id)])
    #         else:
    #             sale_normal_invoice_ids = self.env['account.invoice'].search(
    #                 [('residual', '>', 0), ('state', '=', 'open'), ('yjzy_type', '=', 'sale'),
    #                  ('type', '=', 'out_invoice')])
    #         sale_back_tax_invoice_ids = self.env['account.invoice'].search(
    #             [('residual', '>', 0), ('state', '=', 'open'), ('yjzy_type', '=', 'back_tax'),
    #              ('type', '=', 'out_invoice')])
            sale_other_invoice_ids = self.env['account.invoice'].search(
                [('residual', '>', 0), ('state', '=', 'open'), ('invoice_attribute', '=', 'other_payment'),
                 ('yjzy_type_1', 'in', ['sale','other_payment_sale']), ('type', '=', 'out_invoice')])
    #         advance_payment_ids = self.env['account.payment'].search(
    #             [('sfk_type', '=', 'ysrld'), ('advance_balance_total', '!=', 0),
    #              ('state', 'in', ['posted', 'reconciled'])])
    #         one.sale_normal_invoice_ids = sale_normal_invoice_ids
    #         one.sale_back_tax_invoice_ids = sale_back_tax_invoice_ids
            one.sale_other_invoice_ids = sale_other_invoice_ids
    #         one.advance_payment_ids = advance_payment_ids
    def compute_tb_po_invoice_ids_count(self):
        for one in self:
            one.tb_po_invoice_ids_count = len(one.tb_po_invoice_ids)

    @api.depends('advance_reconcile_order_line_ids','advance_reconcile_order_line_ids.order_id.state',
                 'advance_reconcile_order_line_ids.amount_advance_org', 'advance_reconcile_order_line_ids.yjzy_payment_id')
    def compute_amount_advance_org_all(self):
        for one in self:
            amount_advance_org_all = sum(x.amount_advance_org for x in one.advance_reconcile_order_line_ids)
            advice_amount_advance_org_all = sum(x.advice_amount_advance_org for x in one.advance_reconcile_order_line_ids)
            one.amount_advance_org_all = amount_advance_org_all
            one.advice_amount_advance_org_all =advice_amount_advance_org_all

    @api.depends('advance_reconcile_order_line_approval_ids', 'advance_reconcile_order_line_approval_ids.amount_advance_org')
    def compute_advance_amount_reconcile_order_line_approval(self):
        for one in self:
            one.advance_amount_reconcile_order_line_approval = sum(x.amount_advance_org for x in one.advance_reconcile_order_line_approval_ids)

    @api.depends('amount')
    def compute_amount_signed_payment(self):
        for one in self:
            amount_signed_payment = 0
            if one.sfk_type in ['rcfkd','fkzl']:
                amount_signed_payment = -one.amount
            elif one.sfk_type == 'rcskd':
                amount_signed_payment = one.amount
            one.amount_signed_payment = amount_signed_payment


    # @api.depends('advance_reconcile_order_approve_ids','advance_reconcile_order_approve_ids.amount_advance_org_new')
    # def compute_advance_reconcile_order_approve_amount(self):
    #     for one in self:
    #         advance_reconcile_order_approve_amount = sum(x.amount_advance_org_new for x in one.advance_reconcile_order_approve_ids)
    #         approve_balance = one.advance_balance_total - advance_reconcile_order_approve_amount
    #         one.advance_reconcile_order_approve_amount = advance_reconcile_order_approve_amount
    #         one.approve_balance = approve_balance
    #1102
    # advance_reconcile_order_approve_ids = fields.One2many('account.reconcile.order', 'yjzy_advance_payment_id',u'预收付-应收付认领已审批',
    #                                                           domain=[('state_1', '=', '40_approve')])
    # advance_reconcile_order_approve_amount = fields.Monetary('预收付-应收付认领审批完成金额', currency_field='yjzy_payment_currency_id',compute=compute_advance_reconcile_order_approve_amount, store=True )
    # approve_balance = fields.Monetary('预收付-应收付认领可认领金额', currency_field='yjzy_payment_currency_id', compute=compute_advance_reconcile_order_approve_amount, store=True )

    @api.depends('partner_id','bank_id')
    def compute_pay_to(self):
        for one in self:
            partner_id = one.partner_id
            bank_id = one.bank_id
            bank_huming = bank_id.huming
            if partner_id.name == '未定义':
                pay_to = bank_huming
            else:
                pay_to = partner_id.name
            one.pay_to = pay_to

    def compute_advance_reconcile_lines_count(self):
        for one in self:
            advance_reconcile_order_line_ids_count = len(one.advance_reconcile_order_line_ids)
            one.advance_reconcile_order_line_ids_count = advance_reconcile_order_line_ids_count

    reconcile_type = fields.Selection([('10_payment_out',u'付款'),
                                       ('20_advance_out','预付'),
                                       ('30_payment_in',u'收款'),
                                       ('40_advance_in',u'预收'),
                                       ('50_reconcile',u'核销')],'认领方式')

    invoice_log_id = fields.Many2one('account.invoice','付款指令以及预收预付认领关联账单')

    pay_to = fields.Char('付款对象', compute = compute_pay_to,store=True)

    print_times = fields.Integer(u'打印次数')
    print_date = fields.Datetime('打印时间')
    print_uid = fields.Many2one('res.users',u'最新打印人员')
    can_print = fields.Boolean('允许打印',default=True)

    amount_signed_payment = fields.Monetary(u'收付金额', currency_field='currency_id',
                                            compute=compute_amount_signed_payment, store=True)

    new_rule = fields.Boolean('是否新规则',default=False)

    yjzy_partner_id = fields.Many2one('res.partner', 'Customer')

    payment_for_goods = fields.Boolean('货款')
    payment_for_back_tax = fields.Boolean('退税')
    payment_for_other = fields.Boolean('其他')


    tb_po_invoice_ids = fields.One2many('tb.po.invoice','yjzy_payment_id','应收付申请单')
    tb_po_invoice_ids_count = fields.Integer('应收付申请单数量', compute=compute_tb_po_invoice_ids_count)

    # sale_normal_invoice_ids = fields.Many2many('account.invoice','p1_id','i1_id','未完成认领货款应收账单',compute='compute_invoice_advance')
    # sale_back_tax_invoice_ids = fields.Many2many('account.invoice','p2_id','i2_id','未完成认领应收退税账单',compute='compute_invoice_advance')
    sale_other_invoice_ids = fields.Many2many('account.invoice','p3_id','i3_id','未完成认领其他应收',compute='compute_invoice_advance')
    # advance_payment_ids = fields.Many2many('account.payment','p4_id','i4_id','未完成认领预收单',compute='compute_invoice_advance')


    reconciling = fields.Boolean('正在认领')
    #903
    account_reconcile_order_line_id = fields.Many2one('account.reconcile.order.line',u'预收付-应收付认领明细') #过账后生成的实际的认领单明细
    account_reconcile_order_line_no_id = fields.Many2one('account.reconcile.order.line.no', u'收付款-应收付认领明细')  # 过账后生成的实际的认领单明细
    account_reconcile_order_id = fields.Many2one('account.reconcile.order',u'应收付认领单',) #过账收生成的实际的认领单



    advance_reconcile_order_ids = fields.One2many('account.reconcile.order','yjzy_advance_payment_id',u'预收付-应收付认领')
    advance_reconcile_order_draft_ids = fields.One2many('account.reconcile.order', 'yjzy_advance_payment_id',u'预收付-应收付认领未审批',
                                                              domain=[('state', '=', 'posted')])
    advance_reconcile_order_draft_ids_count = fields.Integer(u'预收付-应收付认领未审批数量',
                                                             compute=_compute_advance_reconcile_order_count_all)
    advance_reconcile_order_no_draft_ids = fields.One2many('account.reconcile.order', 'yjzy_advance_payment_id',
                                                        u'预收付-应收付非草稿',
                                                        domain=[('state', 'not in', ['draft','cancelled','refused'])])
    advance_reconcile_order_no_draft_ids_count = fields.Integer(u'预收付-应收付非草稿数量',
                                                             compute=_compute_advance_reconcile_order_count_all)

    advance_reconcile_order_draft_amount_advance = fields.Float('预收付-应收付认领未审批金额',compute=_compute_advance_reconcile_order_count_all)



    advance_reconcile_order_count_all = fields.Integer(u'预收付-应收付认领数量', compute=_compute_advance_reconcile_order_count_all )
    advance_reconcile_order_count_char = fields.Char(u'预收付-应收付认领未审批数量/全部', compute=_compute_advance_reconcile_order_count_all)
    advance_reconcile_order_no_draft_count_char = fields.Char(u'预收付-应收付认领未审批数量/非草稿', compute=_compute_advance_reconcile_order_count_all)

    #老的
    yshx_ids = fields.One2many('account.reconcile.order', 'yjzy_payment_id', u'收款-应收认领单')
    advance_reconcile_order_line_ids = fields.One2many('account.reconcile.order.line', 'yjzy_payment_id',
                                                       string='预收认领明细', domain=[('amount_advance_org', '>', 0),
                                                                                ('order_id.state', '=', 'done')])
    advance_reconcile_order_line_ids_count = fields.Integer('预收付认领明细数量',compute=compute_advance_reconcile_lines_count)

    advance_reconcile_order_line_approval_ids = fields.One2many('account.reconcile.order.line', 'yjzy_payment_id',
                                                       string='审批中的预收认领明细', domain=[('amount_advance_org', '>', 0),
                                                                                ('order_id.state_1', 'in', ['advance_approval','manager_approval'])])
    advance_amount_reconcile_order_line_approval = fields.Float('预收付-应收付认领未审批金额',compute=compute_advance_amount_reconcile_order_line_approval,store=True)
    #1119计算建议预收预付金额
    amount_advance_org_all = fields.Float('实际已经支付完成的认领金额总额',compute=compute_amount_advance_org_all, store=True)
    advice_amount_advance_org_all = fields.Float('实际已经支付完成的原则分配总额',compute=compute_amount_advance_org_all, store=True)





    #日常收款单：10，25，50，60
    #收款-预收认领单：10，20，50，60
    #收款-应收认领单：10，20，50，60
    #预收-应收认领单：10，20，50，60
    #日常付款单：10，25，50，60
    #应付-付款申请单：10，30，40，50，付款单从25-50，此处40-50，之后判断付款单余额是否为0，如果是，50-60
    #预付-付款申请单：10，20，30，40，50，60 付款单从25-50，此处40-50，之后判断付款单余额是否为0，如果是，50-60
    #应付-预付申请单：10，20，30，50付款单从25-50，此处40-50，之后判断预付款单余额是否为0，如果是，50-60
    state_1 = fields.Selection([('10_draft',u'草稿'),

                                ('20_account_submit',u'待财务审批'),
                                ('25_cashier_submit',u'待出纳审批'),
                                ('30_manager_approve',u'待总经理审批'),
                                ('35_account_approve', u'待会计核对确认'),
                                ('40_approve',u'审批完成'),
                                ('50_posted',u'等待完成认领'),
                                ('60_done',u'完成'),#认领全部完成
                                ('70_checked',u'已对账'),
                                ('80_refused',u'已拒绝'),
                                ('90_cancel',u'已取消')],u'审批状态',track_visibility='onchange',default='10_draft')

    state_fkzl = fields.Selection([
        ('05_fksq', u'待创建付款指令'),
        ('07_post_fkzl',u'已提交付款指令'),
        ('10_draft', u'付款指令待审批'),
        ('20_wait_pay', u'付款指令待支付'),
        ('30_done',u'完成'),
        ('80_refused', u'已拒绝'),
        ('90_cancel', u'已取消')],
        u'付款指令审批状态', track_visibility='onchange', default='10_draft')

    #819增加汇率字段

    # zlsx = fields.Selection([('fkzl',u'付款指令'),('fksq',u'付款申请'),('fkzl_fksq',u'付款指令和申请')],u'指令付款属性') #鉴定这个付款单的指令和付款属性，可以用来综合历史数据

    advance_type = fields.Selection([('10_no_contract',u'无合同'),
                                     ('20_contract',u'有合同')],u'预付类型',compute=compute_advance_type, default='10_no_contract',store=True)
    current_date_rate = fields.Float(u'当日汇率')
    #新增
    payment_comments = fields.Text(u'收付款备注')
    fault_comments = fields.Text('异常备注')
    display_name = fields.Char(u'显示名称', compute=compute_display_name)

    advance_reconcile_order_count = fields.Integer(u'应收认领数量', compute=compute_count)
    advance_reconcile_order_line_amount_char = fields.Text(related='so_id.advance_reconcile_order_line_amount_char', string=u'预收认领明细金额')
    advance_reconcile_order_line_date_char = fields.Text(related='so_id.advance_reconcile_order_line_date_char',string=u'预收认领日期')
    advance_reconcile_order_line_invoice_char = fields.Text(related='so_id.advance_reconcile_order_line_invoice_char',string=u'账单')
    advance_balance_total = fields.Monetary(u'预收余额', compute=compute_advance_balance_total, currency_field='yjzy_payment_currency_id', store=True)


    advance_total = fields.Monetary(u'预收认领金额', compute=compute_advance_balance_total,
                                            currency_field='yjzy_payment_currency_id', store=True)
    rcskd_amount = fields.Monetary(u'收款单金额',related='yjzy_payment_id.amount')
    rcskd_date = fields.Date(u'收款日期', related='yjzy_payment_id.payment_date' )

    partner_confirm_id = fields.Many2one('res.partner','确定的客户',compute='_compute_partner_confirm_id')

    yshxd_amount_payment_org_total = fields.Float(u'应收认领金额',compute=compute_rcskd_amount_total, store=True)
    ysrld_amount_total = fields.Float(u'预收认领金额',compute=compute_rcskd_amount_total, store=True)
    ysrld_amount_advance_total = fields.Float(u'预收被认领金额',compute=compute_rcskd_amount_total, store=True)
    ysrld_amount_advance_balance_total = fields.Float(u'预收未被认领金额',compute=compute_rcskd_amount_total, store=True)
    #13ok
    name = fields.Char(u'编号', default=lambda self: self._default_name())
    sfk_type = fields.Selection(sfk_type, u'收付类型')
    gongsi_id = fields.Many2one('gongsi', '内部公司',default=lambda self:self.env.user.company_id.id)
    #----
    state = fields.Selection(selection_add=[('approved', u'已审批')])
    payment_type = fields.Selection(selection_add=[('claim_in', u'收款认领'), ('claim_out', u'付款认领')])

    tba_id = fields.Many2one('transport.bill.account', u'出运报关金额')
    line_ids = fields.One2many('account.payment.item', 'payment_id', u'付款明细')
    ###invoice_ids = fields.fk_jouMany2many('account.invoice', compute=compute_invoice_ids)
    diff_account_id = fields.Many2one('account.account', u'差异科目')
    diff_amount = fields.Monetary(u'差异金额', currency_field='currency_id')
    yjzy_payment_id = fields.Many2one('account.payment', u'选择收款单')

    # yjzy_advance_payment_id = fields.Many2one('account.payment', u'预收认领单')#给最后核销生成的payment作为核销参考
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'认领余额', related='yjzy_payment_id.balance', currency_field='yjzy_payment_currency_id')

    is_renling = fields.Boolean(u'可以被认领')
    be_renling = fields.Boolean(u'是否认领单')
    balance = fields.Monetary(u'余额', compute=compute_balance, store=True)

    aml_ids = fields.One2many('account.move.line', 'new_payment_id', u'余额相关分录')



    po_id = fields.Many2one('purchase.order', u'采购单')
    supplier_payment_term_id = fields.Many2one('account.payment.term',u'供应商付款条款',related='partner_id.property_supplier_payment_term_id')
    purchase_payment_term_id = fields.Many2one('account.payment.term',u'采购合同付款条款',related='po_id.payment_term_id' )
    po_id_currency_id = fields.Many2one('res.currency', related='po_id.currency_id')
    po_amount = fields.Monetary(u'采购合同总金额',currency_field='po_id_currency_id',related='po_id.amount_total')
    po_pre_advance = fields.Monetary(u'应付预付款',currency_field='po_id_currency_id',related='po_id.pre_advance')
    po_real_advance = fields.Monetary(u'预付金额', currency_field='po_id_currency_id',related='po_id.real_advance')

    so_id = fields.Many2one('sale.order', u'销售合同')
    so_id_currency_id = fields.Many2one('res.currency', related='so_id.currency_id')
    amount_total_so = fields.Monetary('合同金额', related='so_id.amount_total', currency_field='so_id_currency_id')
    customer_payment_term_id = fields.Many2one('account.payment.term', u'客户付款条款',
                                               related='partner_id.property_payment_term_id')
    sale_payment_term_id = fields.Many2one('account.payment.term', u'销售单付款条款', related='so_id.payment_term_id')


    so_pre_advance = fields.Monetary(u'应收预收款', currency_field='so_id_currency_id', related='so_id.pre_advance')
    so_real_advance = fields.Monetary(u'预收金额', currency_field='so_id_currency_id', related='so_id.real_advance')



    expense_id = fields.Many2one('hr.expense', u'费用明细')
    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告', related='expense_id.sheet_id', store=True)
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')

    sale_uid = fields.Many2one('res.users', u'业务员', default=lambda self: self.env.user.assistant_id.id)
    assistant_uid = fields.Many2one('res.users', u'助理', default=lambda self: self.env.user.id)
    fk_journal_id = fields.Many2one('account.journal', u'付款日记账', domain=[('type', 'in', ['cash', 'bank'])])
    include_tax = fields.Boolean(u'是否含税')



    payment_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预收认领和预付申请')

    ysrld_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预收认领单', domain=[('sfk_type','=','ysrld')])
    yfsqd_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预付申请单', domain=[('sfk_type','=','yfsqd')])



    #ptskrl_ids = fields.One2many('yjzy.account.payment', 'yjzy_payment_id', u'普通收款认领单')
    fybg_ids = fields.One2many('hr.expense.sheet', 'payment_id', u'费用报告')
    expense_ids = fields.One2many('hr.expense', 'yjzy_payment_id',  u'费用明细')
    back_tax_invoice_ids = fields.Many2many('account.invoice',   string=u'退税发票')

    count_ysrld = fields.Integer(u'预收认领单数量', compute=compute_count)
    count_yfsqd = fields.Integer(u'预付申请单数量', compute=compute_count)

    count_yshx = fields.Integer(u'应收核销单数量', compute=compute_count)
    #count_ptskrl = fields.Integer(u'普通收款认领单数量', compute=compute_count)
    count_fybg = fields.Integer(u'费用报告数量', compute=compute_count)

    is_editable = fields.Boolean(u'可编辑')
    active = fields.Boolean(u'归档', default=True)

    jiehui_amount = fields.Float('结汇本币余额')
    jiehui_amount_currency = fields.Float('结汇外币余额')
    jiehui_rate = fields.Float(u'结汇平均汇率', default=1)
    jiehui_in_amount = fields.Float('结汇转入余额')

    payment_date_confirm = fields.Datetime('付款确认时间') ##akiny 付款确认时间

    post_uid = fields.Many2one('res.users',u'审批人')
    post_date = fields.Date(u'审批时间')


    # def create_account_bank_statement(self):
    #     print('invoice_ids', self.ids)
    #     print('partner_id', len(self.mapped('partner_id')))
    #     sfk_type = 'yfhxd'
    #     # name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
    #     account_bank_statement_obj = self.env['account.bank.statement']
    #     form_view = self.env.ref('account.view_bank_statement_form')
    #     for one in self:
    #         for x in one.yjzy_invoice_wait_payment_ids:  # 参考M2M的自动多选  剩余应付金额！=0的额外账单
    #             invoice_dic.append(x.id)
    #         print('amount_payment_can_approve_all_akiny', one.amount_payment_can_approve_all)
    #         if one.amount_payment_can_approve_all != 0:  # 考虑已经提交审批的申请
    #             invoice_dic.append(one.id)
    #     print('invoice_dic', invoice_dic)
    #     # test = [(for x in line.yjzy_invoice_all_ids) for line in self)]
    #     # invoice_ids = self.env['account.invoice'].search([('id','in',invoice_dic)])
    #     # with_context(
    #     #     {'fk_journal_id': 1, 'default_be_renling': 1, 'default_invoice_ids': invoice_dic,
    #     #      'default_payment_type': 'outbound', 'show_so': 1, 'default_sfk_type': 'yfhxd', }).
    #
    #     account_reconcile_id = account_reconcile_order_obj.create({
    #         'partner_id': self[0].partner_id.id,
    #         'manual_payment_currency_id': self[0].currency_id.id,
    #         'invoice_ids': [(6, 0, invoice_dic)],
    #         'payment_type': 'outbound',
    #         'partner_type': 'supplier',
    #         'sfk_type': 'yfhxd',
    #         'be_renling': True,
    #         'name': name,
    #         'journal_id': journal.id,
    #         'payment_account_id': bank_account.id,
    #         # 'operation_wizard':operation_wizard,
    #
    #         'purchase_code_balance': 1,
    #         'invoice_attribute': attribute,
    #         'invoice_partner': self[0].invoice_partner,
    #         'name_title': self[0].name_title
    #     })
    #
    #     if account_reconcile_id.invoice_attribute in ['other_po', 'expense_po', 'other_payment']:
    #         account_reconcile_id.operation_wizard = '10'
    #         account_reconcile_id.hxd_type_new = '40'
    #         account_reconcile_id.make_lines()
    #     else:
    #         if account_reconcile_id.supplier_advance_payment_ids_count == 0:  # 如果相关的预付单数量=0，跳过第一步的预付认领
    #             account_reconcile_id.operation_wizard = '10'
    #             account_reconcile_id.hxd_type_new = '40'
    #             account_reconcile_id.make_lines()
    #         else:
    #             account_reconcile_id.operation_wizard = '03'
    #             account_reconcile_id.hxd_type_new = '40'
    #
    #     return {
    #         'type': 'ir.actions.act_window',
    #         'view_mode': 'form',
    #         'res_model': 'account.reconcile.order',
    #         'views': [(form_view.id, 'form')],
    #         'res_id': account_reconcile_id.id,
    #         'target': 'current',
    #         'context': {'default_sfk_type': 'yfhxd',
    #                     'show_po': 1,
    #                     }
    #     }

    #1126
    def make_reconcile_line_ids(self):
        ctx_hxd = self.env.context.get('hxd_id')
        hxd_id = self.env['account.reconcile.order'].search([('id','=',ctx_hxd)],limit=1)
        hxd_id.with_context({'advance_payment_id':self.id}).make_lines_11_16()


        print('hxd_id_akiny',hxd_id,ctx_hxd)



    #原生会计核销单独方法
    def action_reconcile(self):
        if self.balance == 0 and self.x_wkf_state == '159':
            self.x_wkf_state = '163'
            self.state_1 = '60_done'
            self.test_reconcile()
            self.write({'state': 'reconciled'})
        elif self.balance == 0 and self.state_1 == '50_posted':  # 参考核销
            self.state_1 = '60_done'
            self.test_reconcile()
            self.write({'state': 'reconciled'})
            print('compute_balance_1111111', self.state_1)
            # elif balance !=0 and one.x_wkf_state == '163':
            #  one.x_wkf_state = '159'
        else:
            pass

    #test 定稿 参考核销
    def test_reconcile(self):
        if self.sfk_type == 'rcskd':
            account = self.env['account.account'].search([('code', '=', '220301'), ('company_id', '=', self.company_id.id)],limit=1)
            # aml_recs = self.env['account.move.line'].search([('new_payment_id','=',self.id),('account_id','=',account.id)])
            aml_recs = self.aml_ids.filtered(lambda x: x.new_payment_id.id == self.id and x.account_id.id == account.id and x.reconciled == False)
            if self.balance == 0:
                wizard = self.env['account.move.line.reconcile'].with_context(active_ids=[x.id for x in aml_recs]).create({})
                wizard.trans_rec_reconcile_full()
                self.state = 'reconciled'
        if self.sfk_type in ['rcfkd','fkzl']:
            account = self.env['account.account'].search([('code', '=', '112301'), ('company_id', '=', self.company_id.id)],limit=1)
            # aml_recs = self.env['account.move.line'].search([('new_payment_id','=',self.id),('account_id','=',account.id)])
            aml_recs = self.aml_ids.filtered(lambda x: x.new_payment_id.id == self.id and x.account_id.id == account.id and x.reconciled == False)
            if self.balance == 0:
                wizard = self.env['account.move.line.reconcile'].with_context(active_ids=[x.id for x in aml_recs]).create({})
                wizard.trans_rec_reconcile_full()
        if self.sfk_type == 'ysrld':
            account = self.env['account.account'].search([('code', '=', '2203'), ('company_id', '=', self.company_id.id)],limit=1)
            # aml_recs = self.env['account.move.line'].search([('new_payment_id','=',self.id),('account_id','=',account.id)])
            aml_recs = self.aml_ids.filtered(lambda x: x.new_advance_payment_id.id == self.id and x.account_id.id == account.id and x.reconciled == False)
            if self.balance == 0:
                wizard = self.env['account.move.line.reconcile'].with_context(active_ids=[x.id for x in aml_recs]).create({})
                wizard.trans_rec_reconcile_full()
        if self.sfk_type == 'yfrld':
            account = self.env['account.account'].search([('code', '=', '1123'), ('company_id', '=', self.company_id.id)],limit=1)
            # aml_recs = self.env['account.move.line'].search([('new_payment_id','=',self.id),('account_id','=',account.id)])
            aml_recs = self.aml_ids.filtered(lambda x: x.new_advance_payment_id.id == self.id and x.account_id.id == account.id and x.reconciled == False)
            if self.balance == 0:
                wizard = self.env['account.move.line.reconcile'].with_context(active_ids=[x.id for x in aml_recs]).create({})
                wizard.trans_rec_reconcile_full()


    def open_wizard_renling(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        if self.so_id:
            ctx.update({
                'default_so_id': self.so_id.id,
                'default_partner_id': self.partner_id.id,
                'default_yjzy_payment_id': self.id,
            })
        else:
            ctx.update({

                'default_partner_id': self.partner_id.id,
                'default_yjzy_payment_id': self.id,
            })


        if self.sfk_type == 'rcskd':
            ysrld_draft_ids = self.ysrld_ids.filtered(lambda x: x.state == 'draft')
            len_ysrld_draft_ids = len(ysrld_draft_ids)
            if self.ysrld_ids and len_ysrld_draft_ids > 0:
                raise Warning('有存在草稿状态的预收认领单，请先完成认领！')
            else:
                form_view = self.env.ref('yjzy_extend.wizard_renling_form')
        if self.sfk_type == 'ysrld':
            form_view = self.env.ref('yjzy_extend.wizard_renling_form_advance')
        return {
            'name': '创建认领',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.renling',
            'views':[(form_view.id,'form')],
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }


    # @api.onchange('yjzy_partner_id')
    # def onchange_yjzy_partner_id(self):
    #     if self.yjzy_partner_id != False:
    #         self.partner_id = self.yjzy_partner_id

    # def action_multi(self):
    #     print('sdfsdfd',self.ysrld_ids.records)

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        if self.sfk_type == 'yfsqd':
            self.bank_id = False
            self.po_id = False



    @api.multi
    def action_multi(self):
        for record in self.ysrld_ids:
            print('record',record)

    def create_tb_po_invoice(self):
        form_view = self.env.ref('yjzy_extend.tb_po_form')
        type = self.env.context.get('default_type')
        yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        type_invoice = self.env.context.get('default_type_invoice')

        tb_po_invoice_obj = self.env['tb.po.invoice']
        tb_po_invoice_id = tb_po_invoice_obj.create({'currency_id':self.currency_id.id,
                                                     'manual_currency_id':self.currency_id.id,
                                                     'type':type,
                                                     'yjzy_type_1':yjzy_type_1,
                                                     'type_invoice':type_invoice,
                                                     'yjzy_payment_id':self.id
                                                     })
        print('tb_po_invoice_id',tb_po_invoice_id)
        return {
            'name': '其他应收申请单',
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': tb_po_invoice_id.id,
            # 'target': 'new',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {}
        }

    def open_account_invoice(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form_in_one')
        tree_view = self.env.ref('yjzy_extend.invoice_new_1_tree')

        return { 'name': u'应收账单',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.invoice',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree'),(form_view.id, 'form')],
                'domain':   [('residual', '>', 0), ('state', '=', 'open'), ('yjzy_type', '=', 'sale'),('type', '=', 'out_invoice')],
                'context':{'yjzy_payment_id':self.id}
                }

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def cancel(self):
        # for rec in self:
        #     if rec.advance_reconcile_order_ids or rec.advance_reconcile_order_line_ids or rec.payment_ids \
        #             or rec.ysrld_ids or rec.yfsqd_ids or rec.yshx_ids or rec.fybg_ids or rec.expense_ids:
        #         raise Warning(u'此单据已经被认领，请先删除对应的认领单！')
        return super(account_payment, self).cancel()


    @api.onchange('amount')
    def onchange_amount(self):
        if self.yjzy_payment_id:
            self.currency_id = self.yjzy_payment_id.currency_id

    @api.multi
    def print_fkzl(self):
        today = fields.datetime.now()
        uid = self.env.user.id
        print_times = self.print_times
        print_times_last = print_times + 1
        self.write({'print_date':today,
                    'print_uid':uid,
                    'can_print':False,
                    'print_times':print_times_last})
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        },self.env.ref('yjzy_extend.action_report_fkzl').report_action(self)

    #913审批流程
    def action_submit(self):
        ctx = self.env.context
        if self.amount <= 0:
            raise Warning('金额不为0!')
        else:
            if ctx.get('default_sfk_type','') == 'rcskd' or self.sfk_type == 'rcskd':
                if self.payment_comments == '':
                    raise Warning('请填写收款备注信息！')
                else:
                    self.state_1 = '25_cashier_submit'
            elif ctx.get('default_sfk_type', '') == 'rcfkd' or self.sfk_type == 'rcfkd':
                if not self.bank_id:
                    raise Warning('请选择付款对象的银行账号!')
                else:
                    self.state_1 = '25_cashier_submit'
                # self.print_fkzl()
                # return self.env.ref('yjzy_extend.action_report_fkzl').report_action(self)
            elif ctx.get('default_sfk_type', '') == 'ysrld' or self.sfk_type == 'ysrld':
                if not self.yjzy_payment_id:
                    raise Warning('请选择认领的收款单!')
                elif self.yjzy_payment_balance < self.amount:
                    raise Warning('认领金额不能大于待认领金额!')
                elif self.amount_total_so < self.amount and self.so_id:
                    raise Warning('认领金额不能大于销售合同金额！')
                else:
                    self.state_1 = '20_account_submit'
            elif ctx.get('default_sfk_type', '') == 'yfsqd' or self.sfk_type == 'yfsqd':
                if not self.bank_id:
                    raise Warning('请选择付款对象的银行账号!')
                if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
                    raise Warning('合同未审批不允许提交!')
                for one in self.po_id.yjzy_payment_ids:
                    if one.state not in ['posted','reconciled']:
                        raise Warning('有存在未完成审批的预付申请，请先完成审批!')
                self.state_1 = '20_account_submit'
            elif ctx.get('default_sfk_type', '') == 'jiehui' or self.sfk_type == 'jiehui':
                if not self.journal_id or not self.advance_account_id:
                    raise Warning('收款或者付款银行没有填写!')
                else:
                    self.state_1 = '25_cashier_submit'
            elif ctx.get('default_sfk_type', '') == 'nbzz' or self.sfk_type == 'nbzz':
                if not self.journal_id or not self.destination_journal_id:
                    raise Warning('收款或者付款银行没有填写!')
                else:
                    self.state_1 = '25_cashier_submit'
            elif ctx.get('default_sfk_type', '') == 'fkzl' or self.sfk_type == 'fkzl':

                self.state_1 = '25_cashier_submit'
                self.state_fkzl = '20_wait_pay'
                self.state = 'approved'
                for one in self.fksqd_2_ids:
                    one.state_1 = '20_account_submit'

    # 日常收款单：10，25，50，60
    # 收款-预收认领单：10，20，50，60
    # 收款-应收认领单：10，20，50，60
    # 预收-应收认领单：10，20，50，60
    # 日常付款单：10，25，50，60
    # 应付-付款申请单：10，30，40，50，付款单从25-50，此处40-50，之后判断付款单余额是否为0，如果是，50-60
    # 预付-付款申请单：10，20，30，40，50，60 付款单从25-50，此处40-50，之后判断付款单余额是否为0，如果是，50-60
    # 应付-预付申请单：10，20，30，50付款单从25-50，此处40-50，之后判断预付款单余额是否为0，如果是，50-60

    # 日常收款单：10，25，50，60

    def action_account_post(self):
        today = fields.date.today()
        ctx = self.env.context
        if ctx.get('default_sfk_type','') == 'yfsqd' or self.sfk_type == 'yfsqd':
            if not self.fk_journal_id:
                raise Warning('请填写付款账号')
            if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
                raise Warning('合同未审批不允许提交!')
            self.write({'state_1': '30_manager_approve'
                        })
        # if ctx.get('default_sfk_type','') == 'yfhxd' and self.:
        #     self.write({'post_uid': self.env.user.id,
        #                 'post_date': today,
        #                 'state_1': '30_manager_approve'
        #                 })
        if ctx.get('default_sfk_type','') == 'ysrld' or self.sfk_type == 'ysrld':
            self.write({'post_uid': self.env.user.id,
                        'post_date': today,
                        'state_1': '50_posted'
                        })
            print('testddddddd',self.sfk_type)
            self.post()
            self.compute_balance()
    def action_cashier_post(self):
        if self.sfk_type =='rcfkd':
            self.write({
                'state_1': '35_account_approve'
                        })
        else:
            today = fields.date.today()
            self.write({'post_uid': self.env.user.id,
                        'post_date': today,
                        'state_1': '50_posted'
                        })
            self.post()
            self.compute_balance()


    def action_account_approve(self):
        today = fields.date.today()
        self.write({'post_uid': self.env.user.id,
                    'post_date': today,
                     'state_1': '50_posted'
                    })
        self.post()
        self.compute_balance()

    def action_ysrld_one_in_all(self):
        if not self.yjzy_payment_id:
            raise Warning('请选择认领的收款单!')
        elif self.yjzy_payment_balance < self.amount:
            raise Warning('认领金额不能大于待认领金额!')
        elif self.amount_total_so < self.amount:
            raise Warning('认领金额不能大于销售合同金额！')
        else:
            self.action_submit()
            self.action_account_post()
            self.yjzy_payment_id.compute_balance()
            self.yjzy_payment_id.test_reconcile()


    def action_manager_post(self):
        if self.po_id and self.po_id.so_id_state not in ['approve', 'sale']:
            raise Warning('合同未完成审批！')
        today = fields.date.today()
        self.write({'post_uid': self.env.user.id,
                    'post_date': today,
                    'state_1': '40_approve'
                    })
        self.create_rcfkd()

    def action_refuse(self,reason):
        if self.sfk_type == 'fkzl':
            self.write({'state_1': '80_refused',
                        'state_fkzl':'80_refused',
                        'state':'draft'
                        })
            # for one in self.fksqd_2_ids:
            #     one.state_fkzl = '05_fksq'
            #     one.state = 'draft'

        for tb in self:
            tb.message_post_with_view('yjzy_extend.payment_template_refuse_reason',
                                      values={'reason': reason, 'name': self.name},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式



    def action_draft_new(self):
        self.write({'state_1': '10_draft',
                    })
        if self.sfk_type == 'fkzl':
            self.write({'state_fkzl': '10_draft',
                        })
        self.action_draft()

    def judge_partner(self):
        if self.partner_id.name == '未定义' and self.sfk_type not in ['rcskd','nbzz','jiehui']:
            raise Warning('合作伙伴不允许未定义！')
        else:
            pass

    def open_reconcile_order_line(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_ysrld_line_tree_view')
        for one in self:
            return {
                'name': u'预收认领明细',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('yjzy_payment_id', '=', one.id)],
                'target':'new'

            }

    def open_reconcile_order_line_yfrld(self):
        self.ensure_one()
        #form_view = self.env.ref('yjzy_extend.view_account_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.account_yfrld_line_tree_view')
        for one in self:
            return {
                'name': u'预付认领明细',
                'view_type': 'form',
                'view_mode': 'tree,form',
                'res_model': 'account.reconcile.order.line',
                'type': 'ir.actions.act_window',
                'views': [(tree_view.id, 'tree')],
                'domain': [('yjzy_payment_id', '=', one.id)],
                'target':'new'

            }

    def update_payment_date_confirm(self):
        for one in self:
            print('===', one)
            one.payment_date_confirm = one.write_date



    @api.onchange('journal_id')
    def _onchange_journal(self):
        res = super(account_payment, self)._onchange_journal()

        if self.sfk_type == 'jiehui':
            balance, foreign_balance, rate = 0, 0, 1

            if self.journal_id:
                account = self.journal_id.default_debit_account_id
                if account:
                    balance, foreign_balance, rate = account.get_balance()

            self.jiehui_amount = balance
            self.jiehui_amount_currency = foreign_balance
            self.jiehui_rate = rate


        return res


    @api.multi
    def name_get(self):
        ctx = self.env.context
        res = []
        for one in self:
            if ctx.get('default_sfk_type', '') == 'ysrld' or one.sfk_type == 'ysrld':
                # name = '%s:%s' % (one.journal_id.name, str(one.balance))
                name = '%s:%s' % ('预收认领单', str(one.advance_balance_total))
            elif ctx.get('default_sfk_type', '') == 'fkzl' or one.sfk_type == 'fkzl':
                name = '%s:%s' % ('付款指令', one.name)
            elif ctx.get('default_sfk_type', '') == 'yfsql' or one.sfk_type == 'yfsql':
                name = '%s:%s' % ('预付申请', one.name)
            elif ctx.get('default_sfk_type', '') == 'rcskd' or one.sfk_type == 'rcskd':
                name = '%s:%s' % ('日常收款单', one.balance)
            elif ctx.get('default_sfk_type', '') == 'nbzz' or one.sfk_type == 'nbzz':
                name = '%s:%s' % ('内部转账', one.name)
            elif ctx.get('bank_amount'):
                name = '%s[%s]' % (one.journal_id.name, str(one.balance))
            elif ctx.get('advance_bank_amount'):
                name = '%s[%s]' % (one.yjzy_payment_id.journal_id.name, str(one.advance_balance_total))
            elif ctx.get('advance_so_amount'):
                if not one.yjzy_payment_id:
                    name = '%s[%s]' % (one.journal_id.name, str(one.balance))
                else:
                    if one.so_id:
                        name = '%s[%s]' % (one.so_id.contract_code, str(one.advance_balance_total))
                    else:
                        name = '%s[%s]' % ('无销售合同', str(one.advance_balance_total))
            elif ctx.get('advance_po_amount'):
                if not one.yjzy_payment_id:
                    name = '%s[%s]' % (one.journal_id.name, str(one.amount))
                else:
                    if one.po_id:
                        print('po_id',one.po_id)
                        name = '%s[%s]' % (one.po_id.contract_code, str(one.advance_balance_total))
                    else:
                        name = '%s[%s]' % ('无采购合同', str(one.advance_balance_total))
            else:
                name = one.name
            res.append((one.id, name))
        return res

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        print('==name_search==', self.env.context)
        res = super(account_payment, self).name_search(name=name, args=args, operator=operator, limit=limit)
        # print('===', res)
        res_ids = [x[0] for x in res]
        products = self.search(['|', ('amount', operator, name), ('journal_id', operator, name)] + args,
                               limit=limit)
        result = products.name_get()
        # print('===2', result)
        for r in result:
            if not (r[0] in res_ids):
                res.append(r)
        # print('===3', res)
        return res


    @api.multi
    def post(self):
        """
        日常付款单 按钮执行 确认的时候，关联的单子执行确认：（日常付款单一定要先执行）
        1.	应付核销单：执行：make_account_move 生成的分录直接过账，invoice_assign_outstanding_credit
        2.	预付申请单：执行post 以及   核销
        3.	费用报告执行action_sheet_move_create，生成的日常付款申请单的核销按钮执行。
        """
        res = super(account_payment, self).post()
        for one in self:
            one.payment_date_confirm = fields.datetime.now()
            if one.sfk_type == 'rcfkd':
                one.payment_date_confirm = fields.datetime.now() ##akiny 增加付款时间
                if one.yshx_ids:
                    # operation_wizard = len(one.yshx_ids.filtered(lambda x: x.reconcile_payment_ids == False))
                    # print('operation_wizard_1111',operation_wizard,)
                    # if operation_wizard > 0 :#通过这个字段，区别一下老的和新的两种认领方式，新的是生成一张应付认领单
                    print('new_rule____1111',one.new_rule)
                    if one.new_rule == False:
                        ac_orders = one.yshx_ids
                        ac_orders.make_done()
                    else:
                        ac_orders = one.yshx_ids
                        for x in ac_orders:
                            x.action_done_new_stage()

                if one.yfsqd_ids:
                    one.yfsqd_ids.post()
                # if one.fybg_ids:
                #     one.fybg_ids.action_sheet_move_create()
                # if one.fybg_ids:
                #     for x in one.fybg_ids:
                #         if x.expense_to_invoice_type != 'to_invoice':
                #             x.action_sheet_move_create()
                #         else:
                #             x.action_to_invoice_done()
                if one.fybg_ids:
                    one.fybg_ids.action_to_invoice_done()

                   # one.fybg_ids.payment_date_store = fields.datetime.now()
                    #akiny增加 费用明细的付款日期的写入
               # if one.expense_ids:
               #     for x in self.expense_ids:
               #         x.payment_date_store = fields.datetime.now()
            if one.sfk_type == 'fkzl':
                one.payment_date_confirm = fields.datetime.now() ##akiny 增加付款时间
                if one.yshx_fkzl_ids:
                    # operation_wizard = len(one.yshx_ids.filtered(lambda x: x.reconcile_payment_ids == False))
                    # print('operation_wizard_1111',operation_wizard,)
                    # if operation_wizard > 0 :#通过这个字段，区别一下老的和新的两种认领方式，新的是生成一张应付认领单
                    print('new_rule____1111',one.new_rule)
                    if one.new_rule == False:
                        ac_orders = one.yshx_ids
                        ac_orders.make_done()
                    else:
                        ac_orders = one.yshx_fkzl_ids
                        for x in ac_orders:
                            x.action_done_new_stage()

                if one.yfsqd_fkzl_ids:
                    one.yfsqd_fkzl_ids.post()
                    for x in one.yfsqd_fkzl_ids:
                        x.write({'state_1': '50_posted'})
                # if one.fybg_ids:
                #     one.fybg_ids.action_sheet_move_create()
                # if one.fybg_ids:
                #     for x in one.fybg_ids:
                #         if x.expense_to_invoice_type != 'to_invoice':
                #             x.action_sheet_move_create()
                #         else:
                #             x.action_to_invoice_done()
                if one.fybg_fkzl_ids:
                    one.fybg_fkzl_ids.action_to_invoice_done()
                for fksqd in one.fksqd_2_ids:
                    fksqd.state = 'posted'
                    fksqd.state_1 = '60_done'
                    fksqd.state_fkzl = '30_done'
                    fksqd.payment_date_confirm = self.payment_date_confirm
                one.state_fkzl = '30_done'
                one.state_1 = '60_done'
            #重新计算so的应付余额
            if one.po_id.source_so_id:
                so = one.po_id.source_so_id
                so.compute_po_residual()

        return res

    @api.onchange('ysrld_ids', 'yshx_ids',  'fybg_ids', 'sfk_type')
    def onchange_select_lines(self):
        print('==',self.sfk_type)
        if self.sfk_type == 'rcfkd':
            self.amount = (sum(self.yfsqd_ids.mapped('amount'))
                           + sum([x.amount_payment_org for x in self.yshx_ids])
                           + sum(self.fybg_ids.mapped('total_amount'))
                           )
        else:
            pass


    def _get_shared_move_line_vals(self, debit, credit, amount_currency, move_id, invoice_id=False):
        """生成分录明细的准备数据"""
        res = super(account_payment, self)._get_shared_move_line_vals(debit, credit, amount_currency, move_id, invoice_id=invoice_id)

        new_payment_id = self.id
        if self.sfk_type in ['ysrld', 'yfsqd', 'rcfksqd', 'rcskrld','yingshourld','yingfurld']:
            if self.fkzl_id:
                new_payment_id = self.fkzl_id.id
            else:
                new_payment_id = self.yjzy_payment_id.id
        new_advance_payment_id = False
        if self.sfk_type in ['ysrld','yfsqd']:
            new_advance_payment_id = self.id
        if self.sfk_type in ['yingshourld','yingfurld']:
            if self.fkzl_id:
                new_advance_payment_id = self.fkzl_id.id
            else:
                new_advance_payment_id = self.yjzy_payment_id.id
        res.update({
            'new_payment_id': new_payment_id,
            'so_id': self.so_id.id,
            'po_id': self.po_id.id,
            'new_advance_payment_id':new_advance_payment_id
        })
        return res


    def create_rcfkd(self):
        if self.yjzy_payment_id:
            return True

        amount = self.amount
        account_code = '112301'
        ctx = {'default_sfk_type': 'rcfkd'}
        advance_account = self.env['account.account'].search([('code', '=', account_code),('company_id', '=', self.company_id.id)],limit=1)
        print('============', advance_account)
        if not self.fk_journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account:
            raise Warning(u'没有找到对应的预处理科目%s' % account_code)

        payment = self.env['account.payment'].with_context(ctx).create({
            'sfk_type': 'rcfkd',
            'payment_type': 'outbound',
            'partner_id': self.partner_id.id,
            'partner_type': amount > 0 and 'supplier' or 'customer',
            'journal_id': self.fk_journal_id.id,
            'currency_id': self.fk_journal_id.currency_id.id,
            'amount': amount,
            'company_id':self.company_id.id,
            'payment_method_id': 2,
            'advance_ok': True,
            'advance_account_id': advance_account.id,
            'bank_id': self.bank_id.id,
            'include_tax': self.include_tax,
            'rckfd_attribute':'advance_payment',
        })
        if payment.sfk_type == 'rcfkd':
            payment.state_fkzl = '05_fksq'
        self.yjzy_payment_id = payment


    def open_reconcile_account_move_line(self):
        sfk_type = self.env.context.get('default_sfk_type', '')
        if sfk_type in ['yfsqd', 'rcfksqd']:
            account = self.env['account.account'].search([('code', '=', '112301'), ('company_id', '=', self.company_id.id)], limit=1)
            return {
                'type': 'ir.actions.act_window',
                'name': _(u'打开核销分录'),
                'res_model': 'account.move.line',
                'view_type': 'form',
                'view_mode': 'tree, form',
                'domain': [('account_id', '=', account.id), ('new_payment_id', '=', self.yjzy_payment_id.id)],
            }

        if sfk_type in ['ysrld', 'rcskrld']:
            account = self.env['account.account'].search([('code', '=', '220301'), ('company_id', '=', self.company_id.id)], limit=1)
            return {
                'type': 'ir.actions.act_window',
                'name': _(u'打开核销分录'),
                'res_model': 'account.move.line',
                'view_type': 'form',
                'view_mode': 'tree, form',
                'domain': [('account_id', '=', account.id), ('new_payment_id', '=', self.yjzy_payment_id.id)],
            }

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment(self):
        if self.yjzy_payment_id:
            self.currency_id = self.yjzy_payment_id.currency_id
        else:
            self.currency_id = self.journal_id.currency_id

    @api.onchange('fk_journal_id')
    def onchange_fk_journal_payment(self):
        if self.env.context.get('default_sfk_type','') == 'yfsqd' and self.fk_journal_id:
            self.currency_id = self.fk_journal_id.currency_id

    @api.onchange('line_ids', 'line_ids.amount')
    def onchange_lines(self):
        total = 0.0
        for line in self.line_ids:
            total += line.amount
        self.amount = total

    #打开预收认领
    def open_ysrl(self):
        form_view = self.env.ref('yjzy_extend.view_ysrld_form')
        tree_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_tree_1')
        # print('currency_id',self.currency_id)
        # return {
        #     'name': u'预收认领单',
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'account.payment',
        #     'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
        #     'domain': [('yjzy_payment_id', '=', self.id),('sfk_type','=','ysrld')],
        #     'context': {'default_sfk_type': 'ysrld',
        #                 'default_payment_type': 'inbound',
        #                 'default_be_renling': True,
        #                 'default_advance_ok': True,
        #                 'default_partner_type': 'customer',
        #                 'default_currency_id':self.currency_id.id,
        #                 'default_yjzy_payment_id': self.id}
        # }
        yjzy_payment_id = self.env.context.get('yjzy_payment_id')
        if not yjzy_payment_id:
            yjzy_payment_id = self.id
        partner_id = self.partner_id
        # if self.yjzy_partner_id:
        #     partner_id = self.yjzy_partner_id

        count_ysrld = self.count_ysrld
        action = self.env.ref('yjzy_extend.action_ysrld_all_new_1').read()[0]
        ctx = {         'default_sfk_type': 'ysrld',
                        'default_payment_type': 'inbound',
                        'default_be_renling': True,
                        'default_advance_ok': True,
                        'default_partner_type': 'customer',
                        'default_currency_id':self.currency_id.id,
                        'default_yjzy_payment_id': yjzy_payment_id,
                        'default_partner_id': partner_id.id}  # 预付-应付
        if count_ysrld >= 1:
            action['views'] = [(tree_view.id, 'tree'), (form_view.id, 'form')]
            action['domain'] = [('id', 'in', self.ysrld_ids.ids), ('sfk_type', '=', 'ysrld')]
            action['context'] = ctx
        else:
            action['views'] = [(form_view.id, 'form')]
            action['context'] = ctx
        # if self.yjzy_partner_id:
        #     self.partner_id = self.yjzy_partner_id
        print('ctx_222', ctx)
        print('action', action)
        return action

    #打开预付认领
    def open_yufurenling(self):
        form_view = self.env.ref('yjzy_extend.view_yfsqd_form')
        tree_view = self.env.ref('yjzy_extend.view_yfsqd_tree')
        return {
            'name': u'预付认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'show_shoukuan': True,
                        'default_sfk_type': 'yfsqd',
                        'default_payment_type': 'outbound',
                        'default_be_renling': True,
                        'default_advance_ok': True,
                        'default_partner_type': 'supplier',
                        'default_currency_id': self.currency_id.id,
                        'default_yjzy_payment_id': self.id}
        }
    #从收款单打开应收核销
    def open_yshx(self):
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
        tree_view = self.env.ref('yjzy_extend.account_yshxd_tree_view_new')
        # return {
        #     'name': u'应收认领单',
        #     'type': 'ir.actions.act_window',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'account.reconcile.order',
        #     'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
        #     'domain': [('yjzy_payment_id', '=', self.id)],
        #     'context': {'default_sfk_type':'yshxd',
        #                 'bank_amount':1,
        #                 'default_operation_wizard':'10',
        #                 'default_payment_type':'inbound',
        #                 'default_be_renling':1,
        #                 'default_partner_type': 'customer',
        #                 'show_so': 1,
        #                 'default_yjzy_payment_id':self.id},
        # }

        count_yshx = self.count_yshx
        action = self.env.ref('yjzy_extend.action_yshxd_all_new_1').read()[0]
        ctx = {'default_sfk_type':'yshxd',
                            'bank_amount':1,
                            'default_operation_wizard':'10',
                            'default_payment_type':'inbound',
                            'default_be_renling':1,
                            'default_partner_type': 'customer',
                            'show_so': 1,
                            'default_yjzy_payment_id':self.id}  # 预付-应付
        if count_yshx >= 1:
            action['views'] = [(tree_view.id, 'tree'), (form_view.id, 'form')]
            action['domain'] = [('id', 'in', self.yshx_ids.ids), ('sfk_type', '=', 'yshxd')]
            action['context'] = ctx
        else:
            action['views'] = [(form_view.id, 'form')]
            action['context'] = ctx
        print('ctx_222', ctx)
        print('action', action)
        return action


    # 从付款单打开应付核销
    def open_yingfuhexiao(self):
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
        tree_view = self.env.ref('yjzy_extend.account_yshxd_tree_view_new')
        return {
            'name': u'应付申请单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_sfk_type':'yshxd',
                        'bank_amount': 1,
                        'default_operation_wizard': '10',
                        'default_payment_type': 'outbound',
                        'default_partner_type': 'supplier',
                        'default_be_renling': True,
                        'show_so': 1,
                        'default_yjzy_payment_id': self.id},
        }



    #从预收认领单打开应收核销单
    def open_ysrld_yshx(self):
        tree_view = self.env.ref('yjzy_extend.account_yshxd_tree_view_new').id
        form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
        return {
            'name': '认领单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'views': [(tree_view, 'tree'), (form_view, 'form')],
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'default_partner_id':self.partner_id.id,
                        'default_sfk_type': 'yshxd',
                        'default_yjzy_advance_payment_id': self.id,
                        'bank_amount': 1,
                        'default_payment_type': 'inbound',
                        'default_be_renling': 1,
                        'default_partner_type': 'customer',
                        'show_so': 1,
                        'default_operation_wizard': '25',
                        'default_hxd_type_new': '10',  # 预付-应付
                        }
        }

    # 从预付款认领单打开应付核销单

    def open_yfsqd_yfhxd(self):
        if self.state not in '50_posted':
            raise Warning('当前状态不允许进行认领')
        tree_view = self.env.ref('yjzy_extend.account_yfhxd_advance_tree_view_new').id
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        advance_reconcile = self.mapped('advance_reconcile_order_ids')
        action = self.env.ref('yjzy_extend.action_yfhxd_all_new_1').read()[0]
        ctx={'default_partner_id':self.partner_id.id,
                            'default_sfk_type': 'yfhxd',
                            'default_yjzy_advance_payment_id': self.id,
                            'advance_po_amount': 1,
                            'default_payment_type': 'outbound',
                            'default_be_renling': 1,
                            'default_partner_type': 'supplier',
                            'show_so': 1,

                            'default_operation_wizard': '25',
                            'default_hxd_type_new':'30',}#预付-应付
        if len(advance_reconcile) >= 1:
            action['views'] = [(tree_view, 'tree'), (form_view, 'form')]
            action['domain'] = [('id', 'in', advance_reconcile.ids),('sfk_type','=','yfhxd')]
            action['context'] = ctx
        # elif len(advance_reconcile) == 1:
        #     action['views'] = [(self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id, 'form')]
        #     action['res_id'] = advance_reconcile.ids[0]
        else:
            action['views'] = [(form_view, 'form')]
            action['context'] = ctx
        print('ctx_222',ctx)
        print('action',action)
        return action

    # def open_yfsqd_yfhxd_new_window_old(self):
    #     if self.state not in '50_posted':
    #         raise Warning('当前状态不允许进行认领')
    #     tree_view = self.env.ref('yjzy_extend.account_yfhxd_advance_tree_view_new').id
    #     form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
    #     advance_reconcile = self.mapped('advance_reconcile_order_ids')
    #     action = self.env.ref('yjzy_extend.action_yfhxd_all_new_1').read()[0]
    #     ctx = {'default_partner_id': self.partner_id.id,
    #            'default_sfk_type': 'yfhxd',
    #            'default_yjzy_advance_payment_id': self.id,
    #            # 'advance_po_amount': 1,
    #            'fk_journal_id': 1,
    #            'default_payment_type': 'outbound',
    #            'default_be_renling': 1,
    #            'default_partner_type': 'supplier',
    #            'show_so': 1,
    #            'open':1,
    #            'default_operation_wizard': '25',
    #            'default_hxd_type_new': '30', }  # 预付-应付
    #     # if len(advance_reconcile) >= 1:
    #     action['views'] = [(tree_view, 'tree'), (form_view, 'form')]
    #     action['domain'] = [('id', 'in', advance_reconcile.ids), ('sfk_type', '=', 'yfhxd')]
    #     action['target'] = 'new'
    #     action['context'] = ctx
    #     # elif len(advance_reconcile) == 1:
    #     #     action['views'] = [(self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id, 'form')]
    #     #     action['res_id'] = advance_reconcile.ids[0]
    #     # else:
    #     #     action['views'] = [(form_view, 'form')]
    #     #     action['context'] = ctx
    #     print('ctx_222', ctx)
    #     print('action', action)
    #     return action

    def open_yfsqd_yfhxd_new_window(self):
        if self.state not in '50_posted':
            raise Warning('当前状态不允许进行认领')
        tree_view = self.env.ref('yjzy_extend.account_yfhxd_advance_tree_view_approve_new').id
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        advance_reconcile = self.mapped('advance_reconcile_order_ids')

        yfhxd_id = self.env.context.get('yfhxd_id')
        yfhxd_id_cool = self.env['account.reconcile.order'].search([('id','=',yfhxd_id)])
        print('yfhxd_id_cool',yfhxd_id_cool,yfhxd_id)
        if yfhxd_id_cool.state == 'draft':
            domain = [('id', 'in', advance_reconcile.ids), ('sfk_type', '=', 'yfhxd')]
        else:
            domain = [('id', 'in', advance_reconcile.ids), ('sfk_type', '=', 'yfhxd'),('state','not in',['draft','refused','cancelled'])]

        return {
            'name': '预付认领单',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(tree_view, 'tree'),(form_view,'form')],
            'target': 'new',
            'domain': domain,
            'context':{'default_partner_id': self.partner_id.id,
               'default_sfk_type': 'yfhxd',
               'default_yjzy_advance_payment_id': self.id,
               # 'advance_po_amount': 1,
               'fk_journal_id': 1,
               'default_payment_type': 'outbound',
               'default_be_renling': 1,
               'default_partner_type': 'supplier',
               'show_so': 1,
               'open': 1,
               'default_operation_wizard': '25',
               'default_hxd_type_new': '30', }
        }




        # tree_view = self.env.ref('yjzy_extend.account_yfhxd_tree_view_new').id
        # form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        # if self.advance_reconcile_order_count_all > 1:
        #     return {
        #         'name': '认领单',
        #         'view_type': 'form',
        #         'view_mode': 'tree,form',
        #         'res_model': 'account.reconcile.order',
        #         'views': [(tree_view, 'tree'), (form_view, 'form')],
        #         'target': 'current',
        #         'type': 'ir.actions.act_window',
        #         'domain': [('yjzy_advance_payment_id', '=', self.id)],
        #         'context': {'default_partner_id':self.partner_id.id,
        #                     'default_sfk_type': 'yfhxd',
        #                     'default_yjzy_advance_payment_id': self.id,
        #                     'bank_amount': 1,
        #                     'default_payment_type': 'outbound',
        #                     'default_be_renling': 1,
        #                     'default_partner_type': 'supplier',
        #                     'show_so': 1,
        #                     'default_operation_wizard': '25',
        #                     'default_hxd_type_new':'30',#预付-应付
        #
        #                     }
        #     }
        # elif self.advance_reconcile_order_count_all == 1:
        #     return {
        #         'name': '认领单',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_model': 'account.reconcile.order',
        #         'views':  [(form_view, 'form')],
        #         'target': 'current',
        #         'type': 'ir.actions.act_window',
        #         'domain': [('yjzy_advance_payment_id', '=', self.id)],
        #         'context': {'default_partner_id': self.partner_id.id,
        #                     'default_sfk_type': 'yfhxd',
        #                     'default_yjzy_advance_payment_id': self.id,
        #                     'bank_amount': 1,
        #                     'default_payment_type': 'outbound',
        #                     'default_be_renling': 1,
        #                     'default_partner_type': 'supplier',
        #                     'show_so': 1,
        #                     'default_operation_wizard': '25',
        #                     'default_hxd_type_new': '30',  # 预付-应付
        #
        #                     }
        #     }
    #从付款认领直接打开应付核销的form
    def open_yfsqd_yfhxd_form(self):
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        return {
            'name': '认领单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view, 'form')],
            'target': 'current',
            'type': 'ir.actions.act_window',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'default_partner_id':self.partner_id.id,
                        'default_sfk_type': 'yfhxd',
                        'default_yjzy_advance_payment_id': self.id,
                        'advance_po_amount': 1,
                        'default_payment_type': 'outbound',
                        'default_be_renling': 1,
                        'default_partner_type': 'supplier',

                        'show_so': 1,
                        'default_operation_wizard': '25',
                        'default_hxd_type_new':'30',#预付-应付

                        }
        }


    def open_yfsqd_yfhxd_form_new(self):
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        invoice_ids = self.env.context.get('default_invoice_ids')
        print('invoice_ids',invoice_ids)
        return {
            'name': '认领单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view, 'form')],
            'target': 'current',
            'type': 'ir.actions.act_window',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'default_partner_id':self.partner_id.id,
                        'default_sfk_type': 'yfhxd',
                        'default_invoice_ids':invoice_ids,
                        'default_yjzy_advance_payment_id': self.id,
                        'fk_journal_id': 1,
                        'default_payment_type': 'outbound',
                        'default_be_renling': 1,
                        'default_partner_type': 'supplier',
                        'show_so': 1,
                        'default_operation_wizard': '05',
                        'default_hxd_type_new':'30',#预付-应付

                        # 'from_tanchuang':1,
                        }
        }
    #从预收账单直接创建认领(从应付申请的时候，明细上创建)   从应付核销单上的预付列表来做认领的动作
    def create_yfsqd_yfhxd_form_new(self):
        default_invoice_ids = self.env.context.get('default_invoice_ids')
        default_yfhxd_id = self.env.context.get('default_yfhxd_id')
        advance_reconcile_order_ids = self.advance_reconcile_order_ids.filtered(lambda x: x.state not in ['done','approved'] and x.yjzy_reconcile_order_id.id == default_yfhxd_id)
        if advance_reconcile_order_ids:
            raise Warning('已经存在未审批的预认领，无法再次创建')
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new_open').id

        invoice_ids_id = default_invoice_ids[0][2] #参考[6,False,[199,299,344]]取[199,299,344]
        print('invoice_ids',invoice_ids_id)
        #判断应付申请单里的发票和预付单上的采购是否有一致的。如果预付单有采购号，过滤掉没有这个采购单号 的发票，如果是0，提醒，不知道预收需不需要
        invoice_ids = self.env['account.invoice'].search([('id','in',invoice_ids_id)])
        invoice_ids_id_po = []
        if self.po_id:
            for line in invoice_ids:
                print('line.po_ids',line.po_ids)
                if self.po_id in line.po_ids:
                    invoice_ids_id_po.append(line.id)
        else:
            invoice_ids_id_po = invoice_ids_id
        if invoice_ids_id_po == []:
            raise Warning('付款单有对应采购，但是选择的发票没有采购单对应')
        default_invoice_ids_id_po = [[6, 0, invoice_ids_id_po]]
        account_reconcile_order_obj = self.env['account.reconcile.order']

        account_reconcile_id = account_reconcile_order_obj.with_context({'fk_journal_id': 1,'default_be_renling': 1,'default_invoice_ids': default_invoice_ids_id_po,'default_payment_type': 'outbound','show_so': 1,'default_sfk_type': 'yfhxd',}).\
                                                          create({'partner_id':self.partner_id.id,
                                                                  'sfk_type': 'yfhxd',
                                                                  #'invoice_ids': [6,0,invoice_ids_1],
                                                                  'yjzy_advance_payment_id': self.id,
                                                                  'payment_type': 'outbound',
                                                                  'be_renling': 1,
                                                                  'partner_type': 'supplier',
                                                                  'operation_wizard': '25',
                                                                  'hxd_type_new': '30',  # 预付-应付
                                                                  'default_yjzy_type':'purchase',
                                                                  'yjzy_reconcile_order_id': default_yfhxd_id
                                                                  })

        # if account_reconcile_id.yjzy_advance_payment_id.po_id:
        #     for line in account_reconcile_id.invoice_ids:
        #         print('line.po_ids',line.po_ids)
        #         if account_reconcile_id.yjzy_advance_payment_id.po_id not in line.po_ids:
        #
        #             account_reconcile_id.invoice_ids = (3, line.id,)



        account_reconcile_id.make_lines()
        account_reconcile_id.compute_advice_amount_advance_org()
        print('account_reconcile_id',account_reconcile_id)
        return {
            'name': '认领单',
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'account.reconcile.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view, 'form')],
            'res_id': account_reconcile_id.id,
            'target': 'new',
            # 'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {'fk_journal_id': 1,
                        'show_so': 1,

                        }
        }

    def action_reconciling(self):
        if self.reconciling == False:
            self.reconciling = True
        else:
            self.reconciling = False

    def action_cancel_reconciling(self):
        self.reconciling = False



    # def open_ptskrl(self):
    #     return {
    #         'name': u'普通收款认领单',
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'tree,form',
    #         'res_model': 'yjzy.account.payment',
    #         'domain': [('yjzy_payment_id', '=', self.id)],
    #         'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
    #     }
    #打开费用报告
    def open_fybg(self):
        form_view = self.env.ref('yjzy_extend.view_hr_expense_sheet_new_form')
        tree_view = self.env.ref('yjzy_extend.hr_expense_sheet_user_can_create_tree')
        return {
            'name': u'费用申请单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('payment_id', '=', self.id)],
            'context': {'default_payment_id': self.id,
                        'default_expense_type_new':'pay_to_exp'},
        }
    #打开其他收入认领
    def open_fybg_qtsr(self):
        form_view = self.env.ref('yjzy_extend.other_income_sheet_view_form')
        tree_view = self.env.ref('yjzy_extend.other_income_sheet_view_tree')
        return {
            'name': u'其他收入',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('payment_id', '=', self.id)],
            'context': {'default_payment_id': self.id,
                        'default_bank_journal_code':'ysdrl'},

        }
    # def open_yushourenling(self):
    #     form_view = self.env.ref('yjzy_extend.view_ysrld_form')
    #     tree_view = self.env.ref('yjzy_extend.view_ysrld_tree')
    #     return {
    #         'name': u'预收认领单',
    #         'type': 'ir.actions.act_window',
    #         'view_type': 'form',
    #         'view_mode': 'tree,form',
    #         'res_model': 'account.payment',
    #         'views': [(tree_view.id, 'tree'),(form_view.id,'form')],
    #         'domain': [('yjzy_payment_id', '=', self.id)],
    #         'context': {'show_shoukuan': True, 'default_sfk_type': 'ysrld', 'default_payment_type': 'inbound', 'default_be_renling': True, 'default_advance_ok': True, 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
    #     }


    def open_tb_po_invoice(self):
        form_view = self.env.ref('yjzy_extend.tb_po_form')
        tree_view = self.env.ref('yjzy_extend.tb_po_invoice_other_payment_tree')
        return {
            'name': u'其他收款认领申请',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'tb.po.invoice',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('yjzy_payment_id', '=', self.id),('yjzy_type_1','in',['sale','other_payment_sale']),('type','=','other_payment')],
            'context': {'search_default_group_by_state':1,
                        'default_type':'other_payment',
                        'default_yjzy_type_1':'other_payment_sale'},

        }




    def open_putongfukuanrenling(self):
        return {
            'name': u'普通付款认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'yjzy.account.payment',
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
        }

    def action_Warning(self):
        if self.partner_id.state != 'done':
            war = '客户正在审批中，请先完成客户的审批'
            raise Warning(war)

    @api.onchange('payment_for_back_tax')
    def onchange_payment_for_back_tax(self):
        if self.payment_for_back_tax:
            self.partner_id = self.env.ref('yjzy_extend.partner_back_tax')
        else:
            partner_id = self.env['res.partner'].search([('name','=','未定义'),('customer','=',True)])
            self.partner_id = partner_id

    @api.onchange('payment_for_goods')
    def onchange_payment_for_goods(self):
        if not self.payment_for_goods:
            partner_id = self.env['res.partner'].search([('name', '=', '未定义'), ('customer', '=', True)])
            self.partner_id = partner_id

    @api.onchange('payment_for_other')
    def onchange_payment_for_other(self):
        partner_id = self.env['res.partner'].search([('name', '=', '未定义'), ('customer', '=', True)])
        self.partner_id = partner_id

    #904 创建预收-应收认领单   收款-应收认领单
    def create_yshxd_ysrl(self):
        invoice_attribute = self.env.context.get('invoice_attribute')
        if self.partner_id.name == '未定义' and self.payment_for_goods :
            raise Warning('请先选择客户，再进行认领')
        yjzy_type = self.env.context.get('default_yjzy_type')
        yshxd_obj = self.env['account.reconcile.order']

        sfk_type = 'yshxd'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)

        if self.sfk_type == 'ysrld':
            yshxd_id = yshxd_obj.create({
                                         'name':name,
                                         'operation_wizard':'25',
                                         'yjzy_advance_payment_id':self.id,
                                         'partner_id':self.partner_id.id,
                                         'sfk_type':'yshxd',
                                         'payment_type':'inbound',
                                         'partner_type':'customer',
                                         'be_renling':True,
                                         'invoice_attribute': 'normal',
                                         'yjzy_type': 'sale',
                                         'hxd_type_new':'10'
                                         })
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
            return {
                'name': '认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view, 'form')],
                'res_id': yshxd_id.id,
                'target': 'current',
                'type': 'ir.actions.act_window',
                'context':{'default_sfk_type': 'yshxd',
                           'active_id':yshxd_id.id
                           }
            }
        elif self.sfk_type == 'rcskd':
            yshxd_id = yshxd_obj.create({
                                         'name': name,
                                         'operation_wizard': '10',
                                         'partner_id': self.partner_id.id,
                                         'sfk_type': 'yshxd',
                                         'payment_type': 'inbound',
                                         'partner_type': 'customer',
                                         'yjzy_payment_id':self.id,
                                         'be_renling': True,
                                         'invoice_attribute': invoice_attribute,
                                         'yjzy_type': yjzy_type,
                'hxd_type_new': '20'
                                         })

            # if self.yjzy_partner_id:
            #     self.partner_id = self.yjzy_partner_id
            form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
            return {
                'name': '应收认领单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.reconcile.order',
                'views': [(form_view, 'form')],
                'res_id': yshxd_id.id,
                'target': 'current',
                'type': 'ir.actions.act_window',
                'context': {'default_sfk_type': 'yshxd',
                            'active_id': yshxd_id.id,
                            'bank_amount': 1,
                            'show_so': 1,
                            }

            }





class account_payment_item(models.Model):
    _name = 'account.payment.item'

    payment_id = fields.Many2one('account.payment', u'付款单')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id', readonly=True, string=u'货币')
    so_id = fields.Many2one('sale.order', u'销售订单')
    amount = fields.Monetary(u'金额')
    diff_amount = fields.Monetary(u'差异金额', currency_field='currency_id')

    @api.onchange('so_id')
    def onchange_so(self):
        self.amount = self.so_id.pre_advance


# 新的分录创建函数，支持多分录明细，支持so关联
def _new_create_payment_entry(self, amount):
    """ Create a journal entry corresponding to a payment, if the payment references invoice(s) they are reconciled.
        Return the journal entry.
    """
    aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)


    #结汇处理逻辑

    print('==hh===', self.sfk_type)
    if self.sfk_type == 'jiehui':
        move = self.env['account.move'].create(self._get_move_vals())


        aml_in_dic = {
            'move_id': move.id,
            'account_id': self.advance_account_id.id,
            'debit': self.jiehui_in_amount,
            'payment_id': self.id,
        }

        amount = self.amount / self.jiehui_rate
        account2 = self.journal_id.default_debit_account_id
        if not account2:
            raise Warning(u'没有找到日记账对应的科目')
        aml_amount_dic = {
            'move_id': move.id,
            'account_id': account2.id,
            'currency_id': self.currency_id.id,
            'amount_currency': self.amount * -1,
            'debit': amount < 0 and -1 * amount or 0,
            'credit': amount > 0 and amount or 0,
            'payment_id': self.id,
        }
        diff_account = self.env['account.account'].search([('code','=','5712'),('company_id','=',self.env.user.company_id.id)], limit=1)
        diff_amount = self.jiehui_in_amount - amount
        if not diff_account:
            raise Warning(u'没有找到汇兑损益科目5712')
        print('====hh====', diff_amount)
        aml_diff_dic = {
            'move_id': move.id,
            'account_id': diff_account.id,
            'debit': diff_amount < 0 and -1 * diff_amount or 0,
            'credit': diff_amount > 0 and diff_amount or 0,
            'payment_id': self.id,
        }

        aml_in = aml_obj.create(aml_in_dic)
        aml_amount = aml_obj.create(aml_amount_dic)
        aml_diff = aml_obj.create(aml_diff_dic)

        move.post()
        return move











    #非结汇处理逻辑
    invoice_currency = False
    if self.invoice_ids and all([x.currency_id == self.invoice_ids[0].currency_id for x in self.invoice_ids]):
        # if all the invoices selected share the same currency, record the paiement in that currency too
        invoice_currency = self.invoice_ids[0].currency_id
    debit, credit, amount_currency, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(amount,
                                                                                                                     self.currency_id,
                                                                                                                     self.company_id.currency_id,
                                                                                                                     invoice_currency)

    move = self.env['account.move'].create(self._get_move_vals())

    print('==_new_create_payment_entry===', self.line_ids, self.invoice_ids)

    # Write line corresponding to invoice payment
    counterpart_aml_records = aml_obj.browse([])
    if not self.line_ids:
        counterpart_aml_dict = self._get_shared_move_line_vals(debit, credit, amount_currency, move.id, False)
        counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
        counterpart_aml_dict.update({'currency_id': currency_id})
        counterpart_aml = aml_obj.create(counterpart_aml_dict)

        print('==_new_create_payment_entry===1', counterpart_aml)

    else:
        for line in self.line_ids:
            line_amount = line.amount * (self.payment_type in ('outbound', 'transfer') and 1 or -1)
            line_debit, line_credit, line_amount_currency, line_currency_id = aml_obj.with_context(
                date=self.payment_date).compute_amount_fields(line_amount,
                                                              line.currency_id,
                                                              self.company_id.currency_id,
                                                              invoice_currency)
            line_counterpart_aml_dict = self._get_shared_move_line_vals(line_debit, line_credit, line_amount_currency, move.id, False)
            line_counterpart_aml_dict.update(self._get_counterpart_move_line_vals(self.invoice_ids))
            line_counterpart_aml_dict.update({'currency_id': line_currency_id, 'so_id': line.so_id.id})
            one_aml = aml_obj.create(line_counterpart_aml_dict)
            counterpart_aml_records += one_aml

            # 销售单记录预收收入的是那个账户(科目)
            line.so_id.advance_account_id = self.journal_id.default_debit_account_id

    # Reconcile with the invoices
    if self.payment_difference_handling == 'reconcile' and self.payment_difference:
        writeoff_line = self._get_shared_move_line_vals(0, 0, 0, move.id, False)
        amount_currency_wo, currency_id = aml_obj.with_context(date=self.payment_date).compute_amount_fields(self.payment_difference,
                                                                                                             self.currency_id,
                                                                                                             self.company_id.currency_id,
                                                                                                             invoice_currency)[2:]
        # the writeoff debit and credit must be computed from the invoice residual in company currency
        # minus the payment amount in company currency, and not from the payment difference in the payment currency
        # to avoid loss of precision during the currency rate computations. See revision 20935462a0cabeb45480ce70114ff2f4e91eaf79 for a detailed example.
        total_residual_company_signed = sum(invoice.residual_company_signed for invoice in self.invoice_ids)
        total_payment_company_signed = self.currency_id.with_context(date=self.payment_date).compute(self.amount,
                                                                                                     self.company_id.currency_id)
        if self.invoice_ids[0].type in ['in_invoice', 'out_refund']:
            amount_wo = total_payment_company_signed - total_residual_company_signed
        else:
            amount_wo = total_residual_company_signed - total_payment_company_signed
        # Align the sign of the secondary currency writeoff amount with the sign of the writeoff
        # amount in the company currency
        if amount_wo > 0:
            debit_wo = amount_wo
            credit_wo = 0.0
            amount_currency_wo = abs(amount_currency_wo)
        else:
            debit_wo = 0.0
            credit_wo = -amount_wo
            amount_currency_wo = -abs(amount_currency_wo)
        writeoff_line['name'] = self.writeoff_label
        writeoff_line['account_id'] = self.writeoff_account_id.id
        writeoff_line['debit'] = debit_wo
        writeoff_line['credit'] = credit_wo
        writeoff_line['amount_currency'] = amount_currency_wo
        writeoff_line['currency_id'] = currency_id
        writeoff_line = aml_obj.create(writeoff_line)
        if counterpart_aml['debit'] or (writeoff_line['credit'] and not counterpart_aml['credit']):
            counterpart_aml['debit'] += credit_wo - debit_wo
        if counterpart_aml['credit'] or (writeoff_line['debit'] and not counterpart_aml['debit']):
            counterpart_aml['credit'] += debit_wo - credit_wo
        counterpart_aml['amount_currency'] -= amount_currency_wo


    # Write counterpart lines
    if not self.currency_id.is_zero(self.amount):
        if not self.currency_id != self.company_id.currency_id:
            amount_currency = 0
        liquidity_aml_dict = self._get_shared_move_line_vals(credit, debit, -amount_currency, move.id, False)
        liquidity_aml_dict.update(self._get_liquidity_move_line_vals(-amount))
        aml2 = aml_obj.create(liquidity_aml_dict)

        print('==_new_create_payment_entry===2', aml2)



    #<jon> 汇兑增加差异分录明细




    # validate the payment
    move.post()

    # reconcile the invoice receivable/payable line(s) with the payment
    if not self.line_ids:
        self.invoice_ids.register_payment(counterpart_aml)
    else:
        for aml in counterpart_aml_records:
            # TODO 对应的发票和对应的分录明细分别过账
            pass

    return move


Account_Payment._create_payment_entry = _new_create_payment_entry
