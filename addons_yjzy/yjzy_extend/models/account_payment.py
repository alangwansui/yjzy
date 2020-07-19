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

            one.count_ysrld = len(self.ysrld_ids)
            one.count_yfsqd = len(self.yfsqd_ids)

            one.count_yshx = len(self.yshx_ids)
            one.count_ptskrl = len(self.ptskrl_ids)
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


    @api.depends('aml_ids','state')
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

            one.balance = balance

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

        if ctx.get('default_sfk_type','') == 'jiehui':
            res.update({
                'partner_id': self.env['res.partner'].search([('name','=','未定义')], limit=1).id
            })

        if ctx.get('active_model', '') == 'account.invoice':
            invoice = self.env['account.invoice'].browse(ctx.get('active_id'))
            if invoice.gongsi_id:
                res.update({'gongsi_id': invoice.gongsi_id.id})

        return res

    @api.depends('advance_reconcile_order_line_ids','amount','advance_reconcile_order_line_ids.amount_advance_org','advance_reconcile_order_line_ids.yjzy_payment_id')
    def compute_advance_balance_total(self):
        for one in self:
            advance_total = sum([x.amount_advance_org for x in one.advance_reconcile_order_line_ids])
            advance_balance_total = one.amount - advance_total
            one.advance_total = advance_total
            one.advance_balance_total = advance_balance_total

    @api.depends('yshx_ids','yshx_ids.amount_advance_org','ysrld_ids','ysrld_ids.state','ysrld_ids.amount','ysrld_ids.advance_total','ysrld_ids.advance_balance_total')
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








    advance_reconcile_order_line_ids = fields.One2many('account.reconcile.order.line', 'yjzy_payment_id', string='预收认领明细',domain=[('amount_advance_org','>',0),('order_id.state','=','done')])
    advance_reconcile_order_line_amount_char = fields.Text(related='so_id.advance_reconcile_order_line_amount_char', string=u'预收认领明细金额')
    advance_reconcile_order_line_date_char = fields.Text(related='so_id.advance_reconcile_order_line_date_char',string=u'预收认领日期')
    advance_reconcile_order_line_invoice_char = fields.Text(related='so_id.advance_reconcile_order_line_invoice_char',string=u'账单')
    advance_balance_total = fields.Monetary(u'预收余额', compute=compute_advance_balance_total, currency_field='yjzy_payment_currency_id', store=True)
    advance_total = fields.Monetary(u'预收认领金额', compute=compute_advance_balance_total,
                                            currency_field='yjzy_payment_currency_id', store=True)
    rcskd_amount = fields.Monetary(u'收款单金额',related='yjzy_payment_id.amount')
    rcskd_date = fields.Date(u'收款日期', related='yjzy_payment_id.payment_date')

    partner_confirm_id = fields.Many2one('res_partner','确定的客户',compute='_compute_partner_confirm_id')

    yshxd_amount_payment_org_total = fields.Float(u'应收认领金额',conpute=compute_rcskd_amount_total, store=True)
    ysrld_amount_total = fields.Float(u'预收认领金额',conpute=compute_rcskd_amount_total, store=True)
    ysrld_amount_advance_total = fields.Float(u'预收被认领金额',conpute=compute_rcskd_amount_total, store=True)
    ysrld_amount_advance_balance_total = fields.Float(u'预收未被认领金额',conpute=compute_rcskd_amount_total, store=True)
    #13ok
    name = fields.Char(u'编号', default=lambda self: self._default_name())
    sfk_type = fields.Selection(sfk_type, u'收付类型')
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    #----
    state = fields.Selection(selection_add=[('approved', u'已审批')])
    payment_type = fields.Selection(selection_add=[('claim_in', u'收款认领'), ('claim_out', u'付款认领')])

    tba_id = fields.Many2one('transport.bill.account', u'出运报关金额')
    line_ids = fields.One2many('account.payment.item', 'payment_id', u'付款明细')
    ###invoice_ids = fields.fk_jouMany2many('account.invoice', compute=compute_invoice_ids)
    diff_account_id = fields.Many2one('account.account', u'差异科目')
    diff_amount = fields.Monetary(u'差异金额', currency_field='currency_id')
    yjzy_payment_id = fields.Many2one('account.payment', u'选择收款单')
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'认领余额', related='yjzy_payment_id.balance', currency_field='yjzy_payment_currency_id')

    is_renling = fields.Boolean(u'可以被认领')
    be_renling = fields.Boolean(u'是否认领单')
    balance = fields.Monetary(u'余额', compute=compute_balance, store=True)

    aml_ids = fields.One2many('account.move.line', 'new_payment_id', u'余额相关分录')

    so_id = fields.Many2one('sale.order', u'报价单')
    po_id = fields.Many2one('purchase.order', u'采购单')
    expense_id = fields.Many2one('hr.expense', u'费用明细')
    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告', related='expense_id.sheet_id', store=True)
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')

    sale_uid = fields.Many2one('res.users', u'业务员')
    assistant_uid = fields.Many2one('res.users', u'助理')
    fk_journal_id = fields.Many2one('account.journal', u'付款日记账', domain=[('type', 'in', ['cash', 'bank'])])
    include_tax = fields.Boolean(u'是否含税')



    payment_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预收认领和预付申请')

    ysrld_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预收认领单', domain=[('sfk_type','=','ysrld')])
    yfsqd_ids = fields.One2many('account.payment', 'yjzy_payment_id', u'预付申请单', domain=[('sfk_type','=','yfsqd')])

    yshx_ids = fields.One2many('account.reconcile.order', 'yjzy_payment_id', u'应收核销单')
    ptskrl_ids = fields.One2many('yjzy.account.payment', 'yjzy_payment_id', u'普通收款认领单')
    fybg_ids = fields.One2many('hr.expense.sheet', 'payment_id', u'费用报告')
    expense_ids = fields.One2many('hr.expense', 'yjzy_payment_id',  u'费用明细')
    back_tax_invoice_ids = fields.Many2many('account.invoice',   string=u'退税发票')

    count_ysrld = fields.Integer(u'预收认领单数量', compute=compute_count)
    count_yfsqd = fields.Integer(u'预付申请单数量', compute=compute_count)

    count_yshx = fields.Integer(u'应收核销单数量', compute=compute_count)
    count_ptskrl = fields.Integer(u'普通收款认领单数量', compute=compute_count)
    count_fybg = fields.Integer(u'费用报告数量', compute=compute_count)

    is_editable = fields.Boolean(u'可编辑')
    active = fields.Boolean(u'归档', default=True)

    jiehui_amount = fields.Float('结汇本币余额')
    jiehui_amount_currency = fields.Float('结汇外币余额')
    jiehui_rate = fields.Float(u'结汇平均汇率', default=1)
    jiehui_in_amount = fields.Float('结汇转入余额')

    payment_date_confirm = fields.Datetime('付款确认时间') ##akiny 付款确认时间


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
            if ctx.get('default_sfk_type', '') == 'ysrld':
                name = '%s:%s' % (one.journal_id.name, one.amount)
            else:
                name = one.name
            res.append((one.id, name))
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
            if one.sfk_type == 'rcfkd':
                one.payment_date_confirm = fields.datetime.now() ##akiny 增加付款时间
                if one.yshx_ids:
                    ac_orders = one.yshx_ids
                    ac_orders.make_done()

                if one.yfsqd_ids:
                    one.yfsqd_ids.post()

                if one.fybg_ids:
                    one.fybg_ids.action_sheet_move_create()
                   # one.fybg_ids.payment_date_store = fields.datetime.now()
                    #akiny增加 费用明细的付款日期的写入
               # if one.expense_ids:
               #     for x in self.expense_ids:
               #         x.payment_date_store = fields.datetime.now()

            #重新计算so的应付余额
            if one.po_id.source_so_id:
                so = one.po_id.source_so_id
                so.compute_po_residual()

        return res

    @api.onchange('ysrld_ids', 'yshx_ids', 'ptskrl_ids', 'fybg_ids', 'sfk_type')
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
        if self.sfk_type in ['ysrld', 'yfsqd', 'rcfksqd', 'rcskrld']:
            new_payment_id = self.yjzy_payment_id.id

        res.update({
            'new_payment_id': new_payment_id,
            'so_id': self.so_id.id,
            'po_id': self.po_id.id,
            'new_advance_payment_id':self.id
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
            'payment_method_id': 2,
            'advance_ok': True,
            'advance_account_id': advance_account.id,
            'bank_id': self.bank_id.id,
            'include_tax': self.include_tax,

        })
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

    @api.onchange('line_ids', 'line_ids.amount')
    def onchange_lines(self):
        total = 0.0
        for line in self.line_ids:
            total += line.amount
        self.amount = total


    def open_ysrl(self):
        return {
            'name': u'预收认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
        }

    def open_yshx(self):
        return {
            'name': u'应收核销单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
        }

    def open_ptskrl(self):
        return {
            'name': u'普通收款认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'yjzy.account.payment',
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'inbound', 'default_partner_type': 'customer', 'default_yjzy_payment_id': self.id},
        }

    def open_fybg(self):
        return {
            'name': u'费用报告',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'hr.expense.sheet',
            'domain': [('payment_id', '=', self.id)],
            'context': {'default_payment_id': self.id},
        }

    def open_yufurenling(self):
        return {
            'name': u'预付认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'outbound', 'default_partner_type': 'supplier', 'default_yjzy_payment_id': self.id},
        }

    def open_yingfuhexiao(self):

        form_view = self.env.ref('yjzy_extend.account_reconcile_order2_form_view')
        tree_view = self.env.ref('yjzy_extend.account_reconcile_order2_tree_view')

        return {
            'name': u'应付款核销单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('yjzy_payment_id', '=', self.id)],
            'context': {'default_payment_type': 'outbound', 'default_partner_type': 'supplier', 'default_be_renling': True, 'default_yjzy_payment_id': self.id},
        }  #[('payment_type', '=', 'outbound'),('be_renling','=',True)]


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
