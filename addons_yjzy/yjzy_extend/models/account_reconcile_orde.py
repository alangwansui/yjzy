# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from .comm import sfk_type
import logging

_logger = logging.getLogger(__name__)
Account_reconcile_Selection =   [('draft',u'草稿'),
                                 ('advance_approval',u'待预付认领审批'),
                                 ('account_approval',u'待财务审批'),
                                 ('manager_approval',u'待总经理审批'),
                                 ('post',u'审批完成待支付'),
                                 ('done',u'完成'),
                                 ('refused', u'已拒绝'),
                                 ('cancel', u'取消'),
                        ]

class AccountReconcileStage(models.Model):

    _name = "account.reconcile.stage"
    _description = "Account Reconcile Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Account_reconcile_Selection, 'State', default=Account_reconcile_Selection[0][0]) #track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_reconcile_users', 'fid', 'tid', 'Users') #可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_reconcile_group', 'gid', 'bid', 'Groups')

class account_reconcile_order(models.Model):
    _name = 'account.reconcile.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '核销单'
    _order = 'date desc'

    @api.depends('manual_payment_currency_id','yjzy_payment_id','fk_journal_id')
    def _compute_payment_currency(self):
        for one in self:
            if one.sfk_type == 'yfhxd':
                if not one.fk_journal_id:
                    one.payment_currency_id = one.invoice_currency_id
                else:
                    one.payment_currency_id = one.fk_journal_id.currency_id
            elif one.sfk_type == 'yshxd':
                if not one.yjzy_payment_id:
                    one.payment_currency_id = one.invoice_currency_id
                else:
                    one.payment_currency_id = one.yjzy_payment_id.currency_id
            else:
                one.payment_currency_id = one.yjzy_payment_id.currency_id



    def compute_advance(self):
        for one in self:
            if not one.line_ids:
                continue
            partner = one.partner_id
            company_currency = one.currency_id
            invoice_currency = one.invoice_currency_id
            amount_advance_residual_org = 0.0
            if one.sfk_type == 'yshxd':
                amount_advance_residual_org = sum(x.advance_residual for x in one.line_ids)
            elif one.sfk_type == 'yfhxd':
                amount_advance_residual_org = sum(x.advance_residual2 for x in one.line_ids)
            amount_advance_residual = one.partner_type == 'customer' and invoice_currency.compute(
                one.amount_advance_residual_org, company_currency) \
                                      or partner.advance_currency_id.compute(partner.amount_purchase_advance_org,
                                                                             company_currency)
            one.amount_advance_residual_org = amount_advance_residual_org
            one.amount_advance_residual = amount_advance_residual

    def compute_by_invoice(self):
        for one in self:
            if not one.line_ids:
                continue
            invoices = one.line_ids.mapped('invoice_id')
            if len(one.invoice_ids.mapped('currency_id')) > 1:
                raise Warning('选择的发票的交易货币不一致')
            #<jon>
            invoice_currency = one.line_ids[0].invoice_currency_id
            company_currency = one.currency_id
            one.invoice_currency_id = invoice_currency
            one.amount_invoice_residual_org = sum([x.residual for x in invoices])
            one.amount_invoice = sum(
                [invoice_currency.with_context(date=x.date_invoice).compute(x.residual, company_currency) for x in
                 invoices])

    @api.depends('fk_journal_id')
    def compute_by_lines(self):
        for one in self:
            date = one.date
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            bank_currency = one.payment_currency_id.with_context(date=date)
            diff_currency = one.payment_currency_id.with_context(date=date)
            payment_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids

            one.amount_advance_org = sum([x.amount_advance_org for x in lines]) #预收预付认领总计
            one.amount_advance = sum([x.amount_advance for x in lines])
            one.amount_bank_org = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]),one.invoice_currency_id)
            one.amount_bank = sum([x.amount_bank for x in lines])
            one.amount_diff_org = diff_currency.compute(sum([x.amount_diff_org for x in lines]),one.invoice_currency_id)
            one.amount_diff = sum([x.amount_diff for x in lines])
            one.amount_payment_org = payment_currency.compute(sum([x.amount_payment_org for x in lines]),one.invoice_currency_id)
            one.amount_payment = sum([x.amount_payment for x in lines])
            one.amount_total_org = sum([x.amount_total_org for x in lines])
            one.amount_total = sum([x.amount_total for x in lines])
            one.amount_exchange = one.amount_invoice - one.amount_total
            one.other_feiyong_amount = one.amount_payment_org + one.feiyong_amount
            one.final_coat = one.other_feiyong_amount - one.back_tax_amount




    def default_bank_currency(self):
        return self.env.user.company_id.currency_id

    def default_diff_currency(self):
        return self.env.user.company_id.currency_id.id

    def default_journal(self):
        domain = [('type', '=', 'misc')]
        sfk_type = self.env.context.get('default_sfk_type', '')
        domain = []
        print('sfk_type',sfk_type)
        if sfk_type == 'yfhxd':
            domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        if sfk_type == 'yshxd':
            domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]

        journal = self.env['account.journal'].search(domain, limit=1)
        return journal and journal.id

    def default_payment_account(self):
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '112301'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        print('bank_account',bank_account)
        return bank_account and bank_account.id

    def default_bank_account(self):
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '5603'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return bank_account and bank_account.id

    def default_diff_account(self):
        account_obj = self.env['account.account']
        diff_account = account_obj.search([('code', '=', '5601'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return diff_account and diff_account.id

    def default_exchange_account(self):
        account_obj = self.env['account.account']
        diff_account = account_obj.search([('code', '=', '5712'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        return diff_account and diff_account.id


    def _default_name(self):
        sfk_type = self.env.context.get('default_sfk_type')
        if sfk_type:
            name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        else:
            name = None
        return name

    def _default_feiyong_product(self):
        try:
            #return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code','=', 'C1102280A')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_back_tax_product(self):
        try:
            return self.env.ref('yjzy_extend.product_back_tax').id
        except Exception as e:
            return None

    def compute_approve_date_uid(self):
        message_id = self.message_ids[0]
        # message_id = self.message_ids.filtered(lambda x: x.author_id.name == '奚海峰')
        if message_id.owner_user_id:
            approve_uid = message_id.owner_user_id
        else:
            approve_uid = message_id.create_uid
        approve_date =message_id.date
        print('message_id',message_id,approve_uid,approve_date)
        self.write({'approve_uid': approve_uid.id,
                    'approve_date':approve_date})

    # def _compute_supplier_advance_payment_ids_char(self):
    #     for one in self:
    #         supplier_advance_payment_ids_char = ''
    #         supplier_advance_payment_ids = self.env['account.payment'].search([('partner_id','=',one.partner_id.id),('sfk_type','=','yfsqd'),('state', 'in', ['posted', 'reconciled'])])
    #         for o in supplier_advance_payment_ids:
    #             supplier_advance_payment_ids_char += '%s %s\n' % (o.po_id.contract_code,o.amount)
    #         self.supplier_advance_payment_ids_char = supplier_advance_payment_ids_char
    @api.depends('partner_id')
    def _compute_supplier_advance_payment_ids(self):
        for one in self:
            po = []
            for x in one.invoice_ids:
                for line in x.invoice_line_ids.mapped('purchase_id'):
                    po.append(line.id)
                po.append(False)                #
                # dic_po_invl = {}
                # for line in inv.invoice_line_ids:
                #     if line.purchase_id:
                #         po = line.purchase_id
                #         if po in dic_po_invl:
                #             dic_po_invl[po] |= line
                #         else:
                #             dic_po_invl[po] = line
                # return dic_po_invl or False
            print('po',po)
            supplier_advance_payment_ids = self.env['account.payment'].search(
                [('partner_id', '=', one.partner_id.id), ('sfk_type', '=', 'yfsqd'),('po_id','in',po),
                 ('state', 'in', ['posted', 'reconciled']),])
            one.supplier_advance_payment_ids_count = len(supplier_advance_payment_ids)
            one.supplier_advance_payment_ids = supplier_advance_payment_ids
            print('one.supplier_advance_payment_ids',one.supplier_advance_payment_ids)
        # self.write({'supplier_advance_payment_ids': [line.id for line in supplier_advance_payment_ids]})

    @api.depends('line_ids','line_ids.amount_advance_org')
    def compute_amount_advance_org_new(self):
        for one in self:
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            lines = one.line_ids
            one.amount_advance_org_new = sum([x.amount_advance_org for x in lines])

    @api.depends('line_ids', 'line_ids.amount_payment_org','payment_currency_id')
    def compute_amount_payment_org_new(self):
        for one in self:
            date = one.date
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            payment_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids
            one.amount_payment_org_new = payment_currency.compute(sum([x.amount_payment_org for x in lines]),
                                                              one.invoice_currency_id)

    @api.depends('line_ids', 'line_ids.amount_bank_org', 'payment_currency_id')
    def compute_amount_bank_org_new(self):
        for one in self:
            date = one.date
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            bank_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids
            one.amount_bank_org_new = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]),
                                                                  one.invoice_currency_id)

    @api.depends('line_ids', 'line_ids.amount_diff_org', 'payment_currency_id')
    def compute_amount_diff_org_new(self):
        for one in self:
            date = one.date
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            diff_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids
            one.amount_diff_org_new = diff_currency.compute(sum([x.amount_diff_org for x in lines]),one.invoice_currency_id)

    @api.depends('line_ids', 'line_ids.amount_diff_org', 'payment_currency_id')
    def compute_amount_total_org_new(self):
        for one in self:
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            lines = one.line_ids
            one.amount_total_org_new = sum([x.amount_total_org for x in lines])



            # bank_currency = one.payment_currency_id.with_context(date=date)
            # diff_currency = one.payment_currency_id.with_context(date=date)
            # payment_currency = one.payment_currency_id.with_context(date=date)
            # lines = one.line_ids
            # one.amount_advance_org = sum([x.amount_advance_org for x in lines]) #预收预付认领总计
            # one.amount_advance = sum([x.amount_advance for x in lines])
            # one.amount_bank_org = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]),one.invoice_currency_id)
            # one.amount_bank = sum([x.amount_bank for x in lines])
            # one.amount_diff_org = diff_currency.compute(sum([x.amount_diff_org for x in lines]),one.invoice_currency_id)
            # one.amount_diff = sum([x.amount_diff for x in lines])
            # one.amount_payment_org = payment_currency.compute(sum([x.amount_payment_org for x in lines]),one.invoice_currency_id)
            # one.amount_payment = sum([x.amount_payment for x in lines])
            # one.amount_total_org = sum([x.amount_total_org for x in lines])
            # one.amount_total = sum([x.amount_total for x in lines])
            # one.amount_exchange = one.amount_invoice - one.amount_total
            # one.other_feiyong_amount = one.amount_payment_org + one.feiyong_amount
            # one.final_coat = one.other_feiyong_amount - one.back_tax_amount

    # def compute_supplier_advance_payment_ids_count(self):
    #     for one in self:
    #         one.supplier_advance_payment_ids_count = len(one.supplier_advance_payment_ids)

    @api.model
    def _default_account_reconcile_stage(self):
        stage = self.env['account.reconcile.stage']
        return stage.search([], limit=1)

    def compute_advance_reconcile_line_draft_all_count(self):
        for one in self:
            one.advance_reconcile_line_draft_all_count = sum(x.advance_reconcile_order_draft_ids_count for x in one.supplier_advance_payment_ids)

    invoice_attribute = fields.Selection(
        [('normal', u'常规账单'),
         ('reconcile', u'核销账单'),
         ('extra', u'额外账单'),
         ('other_po', u'直接增加'),
         ('expense_po', u'费用转换'),
         ('other_payment',u'其他')], '账单类型')

    stage_id = fields.Many2one(
        'account.reconcile.stage',
        default=_default_account_reconcile_stage)
    state_1 = fields.Selection(Account_reconcile_Selection, u'审批流程', default='draft', index=True, related='stage_id.state',
                               track_visibility='onchange')  # 费用审批流程
    #0911
    #核销单分预收付-应收付，应收付-收付款
    hxd_type_new = fields.Selection([('10', u'预收-应收'),
                                     ('20', u'应收-收款'),
                                     ('30', u'预付-应付'),
                                     ('40', u'应付-付款'),
                                     ('50', u'核销-应收'),
                                     ('60', u'核销-应付')],'认领来源')
    #908
    # supplier_advance_payment_ids_char = fields.Char(u'相关预付',compute=_compute_supplier_advance_payment_ids_char)

    advance_reconcile_line_draft_all_count = fields.Integer('未完成审批的预付认领单数量',compute=compute_advance_reconcile_line_draft_all_count)

    expense_sheet_id = fields.Many2one('hr.expense.sheet',u'费用报告')
    supplier_advance_payment_ids = fields.Many2many('account.payment',u'相关预付', compute=_compute_supplier_advance_payment_ids)
    supplier_advance_payment_ids_count = fields.Integer('相关预付数量',compute=_compute_supplier_advance_payment_ids)
    #903
    reconcile_payment_ids = fields.One2many('account.payment','account_reconcile_order_id',u'认领单')
    yjzy_advance_payment_id = fields.Many2one('account.payment',u'预收认领单')#从预收认领单创建过滤用
    yjzy_advance_payment_balance = fields.Monetary('预付款单余额',related='yjzy_advance_payment_id.advance_balance_total')
    #0901
    approve_date = fields.Datetime(u'审批完成时间')
    approve_uid = fields.Many2one('res.users',u'审批人')

    #828
    comments = fields.Text('备注')
    #827
    operation_wizard = fields.Selection([('03',u'预收付前置'),
                                         ('05',u'创建明细行'),
                                         ('10', u'收付认领'),
                                         ('20', u'预收认领'),
                                         ('25', u'预收简易认领'),
                                         ('30', u'同时认领'),
                                         ('40', u'核销')],'认领方式')    #akiny
    reconcile_type = fields.Selection([('normal',u'正常阶段'),('un_normal',u'核销阶段')],string=u'阶段', default='normal')
    name = fields.Char(u'编号', default=lambda self: self._default_name())
    payment_type = fields.Selection([('outbound', u'付款'), ('inbound', u'收款'), ('claim_in', u'收款认领'), ('claim_out', u'付款认领')], string=u'收/付款',
                                    required=True)
    partner_type = fields.Selection([('customer', u'客户'), ('supplier', u'供应商')], string=u'伙伴类型', )
    journal_id = fields.Many2one('account.journal', u'日记账', required=True, default=lambda self: self.default_journal())
    company_id = fields.Many2one('res.company', string=u'公司', required=True, default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', u'合作伙伴', required=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string=u'公司货币', store=True, index=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', compute=compute_by_invoice)
    state = fields.Selection([('draft', u'草稿'),
                              ('posted', u'待审批'),
                              ('approved', u'批准'),
                              ('done', u'完成'),
                              ('refused',u'拒绝'),
                              ('cancelled', u'取消')],
                             readonly=True, default='draft', copy=False, string=u"状态",track_visibility='onchange')
    date = fields.Date(u'确认日期', index=True, required=True, default=lambda self: fields.date.today())
    # invoice_ids_new = fields.One2many('account.invoice', 'reconcile_order_id', u'发票')#为了直接从发票创建预付-应付申请
    invoice_ids = fields.Many2many('account.invoice', string= u'发票')
    payment_account_id = fields.Many2one('account.account', u'收款科目', required=True,
                                         default=lambda self: self.default_payment_account())
    bank_account_id = fields.Many2one('account.account', u'银行扣款科目', required=False,
                                      default=lambda self: self.default_bank_account())
    diff_account_id = fields.Many2one('account.account', u'销售费用科目', required=True,
                                      default=lambda self: self.default_diff_account())
    exchange_account_id = fields.Many2one('account.account', u'汇兑差异科目', required=True,
                                          default=lambda self: self.default_exchange_account())
    #payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='yjzy_payment_id.currency_id', readonly=True)
    #payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='fk_journal_id.currency_id', readonly=True)
    payment_currency_id = fields.Many2one('res.currency', u'收款货币', compute=_compute_payment_currency,readonly=True)
    manual_payment_currency_id = fields.Many2one('res.currency', u'收款货币:手动输入')
    manual_currency_id = fields.Many2one('res.currency', u'手动设置收款货币')

    # 1银行扣款和销售费用的货币随收款货币；
    # bank_currency_id = fields.Many2one('res.currency', u'银行扣款货币', required=True,
    #                                    default=lambda self: self.default_bank_currency())
    # diff_currency_id = fields.Many2one('res.currency', u'销售费用货币', required=True,
    #                                    default=lambda self: self.default_diff_currency())

    amount_invoice_org = fields.Monetary(u'发票金额', currency_field='invoice_currency_id', compute=compute_by_invoice)

    amount_invoice_residual_org = fields.Monetary(u'发票余额', currency_field='invoice_currency_id', compute=compute_by_invoice)

    amount_advance_residual_org = fields.Monetary(u'待核销预收', currency_field='invoice_currency_id',
                                                  compute=compute_advance)
    amount_advance_org = fields.Monetary(u'使用预收', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_advance_org_new = fields.Monetary(u'使用预收', currency_field='invoice_currency_id', store=True, compute=compute_amount_advance_org_new)#0909新
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_payment_org_new = fields.Monetary(u'收款金额', currency_field='invoice_currency_id', compute=compute_amount_payment_org_new, store=True)#0909新
    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_bank_org_new = fields.Monetary(u'银行扣款', currency_field='invoice_currency_id', compute=compute_amount_bank_org_new, store=True)#0909新
    amount_diff_org = fields.Monetary(u'销售费用', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_diff_org_new = fields.Monetary(u'销售费用', currency_field='invoice_currency_id', compute=compute_amount_diff_org_new,store=True)#0909新
    # amount_exchange_org = fields.Monetary(u'汇兑差异', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_total_org = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_by_lines, store=False)
    amount_total_org_new = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_amount_total_org_new,
                                       store=True)#0909新
    amount_invoice = fields.Monetary(u'发票金额', currency_field='currency_id', compute=compute_by_invoice)
    amount_advance_residual = fields.Monetary(u'待核销预收', currency_field='currency_id', compute=compute_advance)
    amount_advance = fields.Monetary(u'使用预收', currency_field='currency_id', compute=compute_by_lines)
    amount_payment = fields.Monetary(u'收款金额', currency_field='currency_id', compute=compute_by_lines)
    amount_bank = fields.Monetary(u'银行扣款', currency_field='currency_id', compute=compute_by_lines)
    amount_diff = fields.Monetary(u'销售费用', currency_field='currency_id', compute=compute_by_lines)
    amount_exchange = fields.Monetary(u'汇兑差异', currency_field='currency_id', compute=compute_by_lines)
    amount_total = fields.Monetary(u'收款合计:本币', currency_field='currency_id', compute=compute_by_lines, store=False)

    line_ids = fields.One2many('account.reconcile.order.line', 'order_id', u'明细')
    line_no_ids = fields.One2many('account.reconcile.order.line.no', 'order_id', u'明细')
    move_ids = fields.One2many('account.move', 'reconcile_order_id', u'分录')

    yjzy_payment_id = fields.Many2one('account.payment', u'选择收款单')
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'认领余额', related='yjzy_payment_id.balance', currency_field='yjzy_payment_currency_id')


    be_renling = fields.Boolean(u'是否认领单')
    sfk_type = fields.Selection(sfk_type, u'收付类型')

    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    sale_uid = fields.Many2one('res.users', u'业务员')
    assistant_uid = fields.Many2one('res.users', u'助理')
    fk_journal_id = fields.Many2one('account.journal', u'付款日记账', domain=[('type', 'in', ['cash', 'bank'])])
    include_tax = fields.Boolean(u'是否含税')

    no_sopo = fields.Boolean(u'发票没有sopo')

    feiyong_amount = fields.Monetary(u'费用金额')
    feiyong_product_id = fields.Many2one('product.product', u'费用产品', domain=[('type','=','service')], default=_default_feiyong_product)
    fygb_id = fields.Many2one('hr.expense.sheet', u'费用报告')

    back_tax_product_id = fields.Many2one('product.product', u'退税产品', domain=[('type', '=', 'service')], default=_default_back_tax_product)
    back_tax_amount = fields.Monetary(u'退税金额')
    back_tax_invoice_id = fields.Many2one('account.invoice', u'退税发票')

    other_feiyong_amount = fields.Monetary('其他费用金额', compute=compute_by_lines)
    final_coat = fields.Monetary('最终成本', compute=compute_by_lines)

    is_editable = fields.Boolean(u'可编辑')
    gongsi_id = fields.Many2one('gongsi', '内部公司')




    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}
#102
    def create_advance_payment_reconcile(self):
        invoice_ids = self.invoice_ids
        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
        account_reconcile_order_obj = self.env['account.reconcile.order']
        yjzy_advance_payment_id = self.supplier_advance_payment_ids.filtered(lambda x: x.reconciling == True)
        if len(yjzy_advance_payment_id) > 1:
            raise Warning('只能选择一个预付单进行预付申请')
        if len(yjzy_advance_payment_id) == 0:
            raise Warning('请选择一个预付单进行申请')
        account_reconcile_id = account_reconcile_order_obj.with_context(
            {'fk_journal_id': 1, 'default_be_renling': 1, 'default_invoice_ids': invoice_ids,
             'default_payment_type': 'outbound', 'show_so': 1, 'default_sfk_type': 'yfhxd', }). \
            create({'partner_id': self.partner_id.id,
                    'sfk_type': 'yfhxd',
                    # 'invoice_ids': invoice_ids,
                    'yjzy_advance_payment_id': self.id,
                    'payment_type': 'outbound',
                    'be_renling': 1,
                    'partner_type': 'supplier',
                    'operation_wizard': '25',
                    'hxd_type_new': '30',  # 预付-应付
                    })
        account_reconcile_id.make_lines()
        yjzy_advance_payment_id.reconciling = False
        print('account_reconcile_id', account_reconcile_id)
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
    #924
    def write(self, vals):
        res = super(account_reconcile_order, self).write(vals)
        self.invoice_ids.write({'state_2':'30_no_account_payment'})
        return res


    def action_05(self):
        self.operation_wizard = '05'
        self.make_lines()


    @api.onchange('yjzy_advance_payment_id')
    def onchange_yjzy_advance_payment_id(self):
        if self.reconcile_payment_ids:
            raise Warning('已经生成认领单，不可修改预付单')
        for one in self.line_no_ids:
            one.yjzy_payment_id = self.yjzy_advance_payment_id
        # for one in self.line_ids:
        #     one.yjzy_payment_id = self.yjzy_advance_payment_id
    #分别创建需要的付款单（原生）
    def create_yjzy_payment_ysrl(self):
        self.ensure_one()
        self.reconcile_payment_ids.unlink()
        sfk_type = 'yingshourld'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        account_payment_obj = self.env['account.payment']
        partner_id = self.partner_id
        yjzy_payment_id = self.yjzy_payment_id
        line_ids = self.line_ids
        journal_domain_yszk = [('code', '=', 'yszk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yszk = self.env['account.journal'].search(journal_domain_yszk, limit=1)
        journal_domain_ysdrl = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_ysdrl = self.env['account.journal'].search(journal_domain_ysdrl, limit=1)
        journal_domain_yhkk = [('code', '=', 'yhkk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yhkk = self.env['account.journal'].search(journal_domain_yhkk, limit=1)
        journal_domain_xsfy = [('code', '=', 'xsfy'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_xsfy = self.env['account.journal'].search(journal_domain_xsfy, limit=1)

        for line in line_ids:
            if line.amount_payment_org >0:
                reconcile_payment_id = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id':partner_id.id,
                    'yjzy_payment_id':yjzy_payment_id.id,
                    'amount':line.amount_payment_org,
                    'currency_id':line.payment_currency_id.id,
                    'sfk_type': sfk_type,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok':False,
                    'journal_id':journal_id_ysdrl.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],#参考m2m
                    'so_id':line.so_id.id,
                })
            if line.amount_advance_org > 0:
                print('journal_id_yszk',journal_id_yszk)
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id': partner_id.id,
                    'amount': line.amount_advance_org,
                    'sfk_type': sfk_type,
                    'currency_id': line.yjzy_currency_id.id,
                    'yjzy_payment':line.yjzy_payment_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_yszk.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'so_id': line.so_id.id,

                })
            if line.amount_bank_org > 0:
                reconcile_payment_id_3 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id': partner_id.id,
                    'amount': line.amount_bank_org,
                    'sfk_type': sfk_type,
                    'currency_id': line.invoice_currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_yhkk.  id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'so_id': line.so_id.id,
                })

            if line.amount_diff_org > 0:
                reconcile_payment_id_4 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id': partner_id.id,
                    'amount': line.amount_diff_org,
                    'sfk_type': sfk_type,
                    'currency_id': line.invoice_currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_xsfy.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'so_id': line.so_id.id,
                })

    def create_yjzy_payment_yfrl(self):
        self.ensure_one()
        self.reconcile_payment_ids.unlink()
        sfk_type = 'yingfurld'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        account_payment_obj = self.env['account.payment']
        partner_id = self.partner_id
        yjzy_payment_id = self.yjzy_payment_id
        line_ids = self.line_ids
        journal_domain_yfzk = [('code', '=', 'yfzk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yfzk = self.env['account.journal'].search(journal_domain_yfzk, limit=1)
        journal_domain_yfdrl = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yfdrl = self.env['account.journal'].search(journal_domain_yfdrl, limit=1)
        journal_domain_yhkk = [('code', '=', 'yhkk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yhkk = self.env['account.journal'].search(journal_domain_yhkk, limit=1)
        journal_domain_xsfy = [('code', '=', 'xsfy'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_xsfy = self.env['account.journal'].search(journal_domain_xsfy, limit=1)

        for line in line_ids:
            if line.amount_payment_org > 0:
                reconcile_payment_id = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'sfk_type': sfk_type,
                    'partner_id': partner_id.id,
                    'yjzy_payment_id': yjzy_payment_id.id,
                    'amount': line.amount_payment_org,
                    'currency_id': line.payment_currency_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_ok': False,
                    'journal_id': journal_id_yfdrl.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'po_id': line.po_id.id,
                })
            if line.amount_advance_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'partner_id': partner_id.id,
                    'amount': line.amount_advance_org,
                    'name':name,
                    'sfk_type': sfk_type,
                    'currency_id': line.yjzy_currency_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_ok': False,
                    'journal_id': journal_id_yfzk.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'po_id': line.po_id.id,

                })
            if line.amount_bank_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'partner_id': partner_id.id,
                    'amount': line.amount_bank_org,
                    'name':name,
                    'sfk_type': sfk_type,
                    'currency_id': line.invoice_currency_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_ok': False,
                    'journal_id': journal_id_yhkk.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)], #akiny参考 m2m
                    'po_id': line.po_id.id,
                })

            if line.amount_diff_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_line_id': line.id,
                    'partner_id': partner_id.id,
                    'amount': line.amount_diff_org,
                    'name':name,
                    'sfk_type': sfk_type,
                    'currency_id': line.invoice_currency_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_ok': False,
                    'journal_id': journal_id_xsfy.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'po_id': line.po_id.id,
                })



    #判断预付金额和预付款单的余额问题
    @api.onchange('line_no_ids')
    def _onchange_line_no_ids(self):
        lines = self.line_no_ids
        if self.yjzy_advance_payment_balance < 0:
            print('yjzy_advance_payment_balance',self.yjzy_advance_payment_balance)
            raise Warning('预付认领大于可认领金额')
        for one in lines:
            if one.amount_advance_org > one.invoice_residual:
                raise Warning('预付认领金额大于可认领的应付金额')
        if self.operation_wizard in ['10','40']:
            self.update_line_amount()
        if self.operation_wizard in ['25']:
            self.update_line_advance_amount()

    def open_wizard_reconcile_invoice(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        if self.sfk_type == 'yshxd':

            ctx.update({
                'default_partner_id': self.partner_id.id,
                'default_order_id':self.id,
                'default_invoice_ids':self.invoice_ids.ids,
                'sfk_type':self.sfk_type,
                'default_yjzy_advance_payment_id':self.yjzy_advance_payment_id.id
            })
            return {
                'name': '添加账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.reconcile.invoice',
                # 'res_id': bill.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        if self.sfk_type == 'yfhxd':
            ctx.update({
                'default_partner_id': self.partner_id.id,
                'default_order_id': self.id,
                'default_invoice_ids': self.invoice_ids.ids,
                'sfk_type': self.sfk_type,
                'default_yjzy_advance_payment_id': self.yjzy_advance_payment_id.id
            })
            return {
                'name': '添加账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.reconcile.invoice',
                # 'res_id': bill.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
    # def open_wizard_reconcile_invoice_yfhxd(self):
    #     self.ensure_one()
    #     ctx = self.env.context.copy()
    #     ctx.update({
    #         'default_partner_id': self.partner_id.id,
    #         'default_order_id':self.id,
    #         'default_invoice_ids':self.invoice_ids.ids,
    #         'sfk_type':self.sfk_type,
    #     })
    #     return {
    #         'name': '添加账单',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'wizard.reconcile.invoice',
    #         # 'res_id': bill.id,
    #         'target': 'new',
    #         'type': 'ir.actions.act_window',
    #         'context': ctx,
    #     }

    def unlink(self):
        for one in self:
            if one.state != 'cancelled':
                raise Warning(u'只有取消状态允许删除')
        return super(account_reconcile_order, self).unlink()

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['account.reconcile.stage'].search(search_domain, order=order, limit=1)

    #审批新
    def action_submit_stage(self):
        self.ensure_one()
        # if self.amount_total_org == 0:
        #     raise Warning('认领金额为0，无法提交！')
        # if self.sfk_type == 'yshxd':
        #     self.action_approve()
        #     stage_id = self._stage_find(domain=[('code', '=', '030')])
        #     self.write({'stage_id': stage_id.id,
        #                 'state': 'posted',
        #                 })
        #     # self.date = fields.date.today()

        if self.sfk_type == 'yfhxd':

            amount_advance_residual_org = self.amount_advance_residual_org
            amount_advance_org = self.amount_advance_org
            if amount_advance_residual_org < amount_advance_org:
                raise Warning(u'预付认领金额大于预付余额')
            if self.hxd_type_new == '30':
                if self.amount_total_org == 0:
                    raise Warning('认领金额为0，无法提交！')
                if self.yjzy_advance_payment_balance < self.amount_advance_org :
                    raise Warning('预付认领金额大于预付款单余额！')

                stage_id = self._stage_find(domain=[('code', '=', '040')])
                self.write({'stage_id': stage_id.id,
                            'state': 'posted',
                            # 'operation_wizard':'25'
                            })
            elif self.hxd_type_new == '40':
                stage_id = self._stage_find(domain=[('code', '=', '020')])
                self.write({'stage_id': stage_id.id,
                            'state': 'posted',
                            # 'operation_wizard':'10'
                            })


            # self.create_customer_invoice()
            # self.create_fygb()
            # for one in self.supplier_advance_payment_ids:
            #     one.reconciling = False
        # self.make_lines()

        return True

    # @api.onchange('amount_advance_org')
    # def onchange_amount_advance_org(self):
    #

    def action_manager_approve_first_stage(self):
        if self.advance_reconcile_line_draft_all_count != 0:
            raise Warning('有未完成审批预付认领，请检查！')
        stage_id = self._stage_find(domain=[('code', '=', '030')])
        self.write({'stage_id': stage_id.id,
                    'state': 'posted',
                    'operation_wizard':'10',
                    })

    # 财务审批：预付没有审批，只有应付申请的时候才会审批。
    def action_account_approve_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '040')])
        self.write({'stage_id': stage_id.id,
                    'state': 'posted',
                    })


    # 总经理审批：如果是预付申请，直接完成makedone，只有应付申请的时候才会审批。
    def action_manager_approve_stage(self):
        self.ensure_one()
        if self.sfk_type == 'yfhxd':
            if self.operation_wizard in ['10', '30']:
                self.create_rcfkd()
                stage_id = self._stage_find(domain=[('code', '=', '050')])
                self.write({'stage_id': stage_id.id,
                            'state': 'approved',
                            'approve_date': fields.date.today(),
                            'approve_uid': self.env.user.id
                            })
            self.create_yjzy_payment_yfrl()
            if self.operation_wizard in ['20', '25']:
                self.action_done_new()
                stage_id = self._stage_find(domain=[('code', '=', '060')])
                self.write({'stage_id': stage_id.id,
                            'state': 'done',
                            'approve_date': fields.date.today(),
                            'approve_uid': self.env.user.id
                            })
       #应收核销待定:
        if self.sfk_type == 'fshxd':
            self.create_yjzy_payment_ysrl()
            self.action_done_new()
            stage_id = self._stage_find(domain=[('code', '=', '060')])
            self.write({'stage_id': stage_id.id,
                        'state': 'approved',
                        'approve_date': fields.date.today(),
                        'approve_uid': self.env.user.id
                        })



        # if self.fygb_id:
        #     fygb = self.fygb_id
        #     fygb.approve_expense_sheets()
        # if self.back_tax_invoice_id:
        #     invoice = self.back_tax_invoice_id
        #     invoice.action_invoice_open()
        # self.create_rcfkd()





    def action_draft_stage(self):
        if self.sfk_type == 'yfhxd':
            self.yjzy_payment_id.unlink()
        stage_id = self._stage_find(domain=[('code', '=', '010')])
        self.write({'stage_id': stage_id.id,
                    'state': 'draft',
                    'approve_date': False,
                    'approve_uid': False
                    })


    def action_refuse_stage(self,reason):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限拒绝')
        else:
            self.write({'stage_id': stage_id.id,
                        'state': 'refused',
                         })
            for tb in self:
                tb.message_post_with_view('yjzy_extend.reconcile_hxd_template_refuse_reason',
                                          values={'reason': reason, 'name': self.name},
                                          subtype_id=self.env.ref(
                                              'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式




    def action_posted_new(self):
        self.ensure_one()
        if self.amount_total_org == 0:
            raise Warning('认领金额为0，无法提交！')
        else:
            if self.sfk_type == 'yshxd':
                amount_payment_org = self.amount_payment_org
                yjzy_payment_balance = self.yjzy_payment_balance
                amount_advance_residual_org = self.amount_advance_residual_org
                amount_advance_org = self.amount_advance_org
                if yjzy_payment_balance < amount_payment_org:
                    raise Warning(u'收款认领金额大于收款单余额')
                if amount_advance_residual_org < amount_advance_org:
                    raise Warning(u'预收认领金额大于预收余额')
                # for x in self.line_ids:
                #     if x.amount_advance_org != 0.0 and x.yjzy_payment_id == False:
                #         raise Warning('有预收单没有选择，请检查！')
                #     if x.amount_payment_org > x.amount_invoice_so_residual:
                #         raise Warning('明细行认领金额大于账单明细可认领金额!')
                #     if x.amount_advance_org > x.advance_residual:
                #         raise Warning('明细行预收认领金额大于账单明细可认领预收金额!')
                # self.state = 'approved'
                self.action_approve_new()
            elif self.sfk_type == 'yfhxd':
                if self.operation_wizard in ['20','25']:
                    self.action_approve_new()
                else:
                    self.state = 'posted'

            #     for x in self.line_ids:
            #         if x.amount_advance_org != 0.0 and x.yjzy_payment_id == False:
            #             raise Warning('有预付单没有选择，请检查！')
            #         if x.amount_payment_org > x.amount_invoice_so_residual:
            #             raise Warning('明细行认领金额大于账单明细可认领金额!')
            #         if x.amount_advance_org > x.advance_residual2:
            #             raise Warning('明细行预付认领金额大于账单明细可认领预付金额!')

        # self.date = fields.date.today()
        return True

    def action_approve_new(self):
        self.ensure_one()
        if self.sfk_type == 'yfhxd':
            if self.operation_wizard in ['10','30']:
                self.create_rcfkd()
            self.create_yjzy_payment_yfrl()
        if self.sfk_type == 'fshxd':
            self.create_yjzy_payment_ysrl()
        self.write({'state': 'approved',
                    'approve_date': fields.date.today(),
                    'approve_uid':self.env.user.id})

    def action_done_new(self):
        self.ensure_one()
        if self.sfk_type == 'yfhxd':
            if self.reconcile_payment_ids:
                self.reconcile_payment_ids.post()


    def action_draft_new(self):
        if self.sfk_type == 'yfhxd':
            self.yjzy_payment_id.unlink()

        self.write({'state': 'draft',
                    'approve_date': False,
                    'approve_uid': False})






    def action_refuse_new(self,reason):
        self.write({'state': 'refused',
                     })
        for tb in self:
            tb.message_post_with_view('yjzy_extend.reconcile_hxd_template_refuse_reason',
                                      values={'reason': reason, 'name': self.name},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式


    def action_posted(self):
        self.ensure_one()
        self.state = 'posted'
        #self.date = fields.date.today()
        if self.sfk_type == 'yshxd':
            self.action_approve()
        elif self.sfk_type == 'yfhxd':
            self.create_customer_invoice()
            self.create_fygb()
        return True


    def action_approve(self):#预付提价的时候
        if self.hxd_type_new in ['10','30']:#预付的时候
            self.make_done()
        else:
            if self.fygb_id:
                fygb = self.fygb_id
                fygb.approve_expense_sheets()
            if self.back_tax_invoice_id:
                invoice = self.back_tax_invoice_id
                invoice.action_invoice_open()
            self.state = 'approved'


    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'

    def action_done(self):
        if self.sfk_type == 'yshxd':
            self.make_done()
            self.state = 'done'
            self.approve_date = fields.date.today()
            self.approve_uid = self.env.user
        elif self.hxd_type_new in ['10','30'] and self.sfk_type == 'yfhxd':#预付的时候
            self.make_done()
        else:
            raise Warning('无法审批！')





    def create_fygb(self):
        self.ensure_one()
        if self.fygb_id:
            return True
            #raise Warning(u'不要重复生成')
        if self.feiyong_amount <= 0:
            return True
            #raise Warning(u'费用金额不能为0')
        if not self.feiyong_product_id:
            return True
            #raise Warning(u'费用产品未设置')

        expense =self.env['hr.expense'].create({
            'name': self.feiyong_product_id.name,
            'product_id': self.feiyong_product_id.id,
            'unit_amount': self.feiyong_amount,
            'quantity': 1,
            'currency_id': self.currency_id.id,
        })
        #ondchange to set jouranl
        expense._onchange_product_id()
        expense.unit_amount = self.feiyong_amount


        fygb = self.env['hr.expense.sheet'].create({
            'name': self.feiyong_product_id.name,
            'include_tax': self.include_tax,
            'partner_id': self.partner_id.id,
            'fk_journal_id': self.fk_journal_id.id,
            'bank_id': self.bank_id.id,
            'journal_id': self.journal_id.id,
            'expense_line_ids': [(4,  expense.id)]
        })

        self.fygb_id = fygb

    def create_customer_invoice(self):
        self.ensure_one()
        if self.back_tax_invoice_id:
            return True
            #raise Warning(u'不要重复生成')
        if self.back_tax_amount <= 0:
            return True
            #raise Warning(u'退税金额不能为0')


        jounal_obj = self.env['account.invoice'].with_context({'type':'out_invoice', 'journal_type': 'sale'})

        pdt = self.back_tax_product_id
        jouranl = jounal_obj._default_journal()
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        invoice_account = self.env['account.account'].search([('code','=','1122'),('company_id', '=', self.env.user.company_id.id)], limit=1)
        pdt_account = pdt.property_account_income_id


        if not invoice_account:
            raise Warning(u'发票科目 1122 未找到')
        if not pdt:
            raise Warning(u'产品 back_tax1 未找到')
        if not pdt_account:
            raise Warning(u'产品 back_tax1 的科目未设置')

        invoice_line_data = {
            'product': pdt.id,
            'name': pdt.name,
            'account_id': pdt_account.id,
            'price_unit': self.back_tax_amount,
            'product_id': pdt.id,
        }
        invoice_id = jounal_obj.create({
            'name': u'草稿发票',
            'partner_id': partner.id,
            'account_id': invoice_account.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        self.back_tax_invoice_id = invoice_id



    def create_rcfkd(self):
        self.ensure_one()
        amount = self.amount_payment_org + self.fygb_id.total_amount
        account_code = '112301'
        ctx = {'default_sfk_type': 'rcfkd'}
        advance_account = self.env['account.account'].search([('code', '=', account_code), ('company_id', '=', self.env.user.company_id.id)], limit=1)

        if not self.fk_journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account:
            raise Warning(u'没有找到对应的预处理科目%s' % account_code)

        back_tax_invoice_data = self.back_tax_invoice_id and  [(4, self.back_tax_invoice_id.id)] or None
        fybg_data = self.fygb_id and [(4, self.fygb_id.id)] or None

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
            'fybg_ids': fybg_data,
            'back_tax_invoice_ids': back_tax_invoice_data,
            'expense_sheet_id':self.expense_sheet_id.id
        })
        if self.expense_sheet_id:
            self.expense_sheet_id.payment_id = payment.id #1009
        self.yjzy_payment_id = payment


    @api.onchange('journal_id')
    def onchange_journal(self):
        self.payment_account_id = self.journal_id.default_debit_account_id

    # @api.onchange('partner_type')
    # def _onchange_partner_type(self):
    #     if self.partner_type:
    #         return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}



    def open_reconcile_account_move_line(self):
        sfk_type = self.env.context.get('default_sfk_type', '')

        if sfk_type == 'yfhxd':
            account = self.env['account.account'].search([('code', '=', '1123'), ('company_id', '=', self.company_id.id)], limit=1)
            return {
                'type': 'ir.actions.act_window',
                'name': _(u'打开核销分录'),
                'res_model': 'account.move.line',
                'view_type': 'form',
                'view_mode': 'tree, form',
                'domain': [('account_id', '=', account.id), ('po_id', 'in', [x.po_id.id for x in self.line_ids])],
            }

        if sfk_type == 'yshxd':
            account = self.env['account.account'].search([('code', '=', '2203'), ('company_id', '=', self.company_id.id)], limit=1)
            return {
                'type': 'ir.actions.act_window',
                'name': _(u'打开核销分录'),
                'res_model': 'account.move.line',
                'view_type': 'form',
                'view_mode': 'tree, form',
                'domain': [('account_id', '=', account.id), ('so_id', 'in', [x.so_id.id for x in self.line_ids])],
            }

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment_id(self):
        self.manual_payment_currency_id = self.yjzy_payment_id.currency_id

    @api.onchange('partner_id')
    def onchange_partner(self):
        ctx = self.env.context.get('default_yjzy_payment_id')
        if self.partner_id:
            self.invoice_ids.write({'reconcile_order_id': None})
            self.line_ids = False
            self.line_no_ids = False
            self.bank_id =False
            self.fk_journal_id = False
            if not ctx:
                self.yjzy_payment_id = False
            if self.hxd_type_new not in  ['30','10']:
                self.yjzy_advance_payment_id = False

    def check_amount(self):
        self.ensure_one()

    def _prepare_account_move(self):
        return {
            'name': self.journal_id.with_context(ir_sequence_date=self.date).sequence_id.next_by_id(),
            'date': self.date,
            'ref': self.name,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
            'gongsi_id': self.gongsi_id.id,
        }

    def _prepare_move_line_account(self, model=''):
        debit_account, credit_account, debit_sign, credit_sign = None, None, 1, 1
        payment_type = self.payment_type
        account_obj = self.env['account.account']
        if model == 'payment':
            if payment_type == 'inbound':
                debit_account = self.payment_account_id
                credit_account = account_obj.search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = 1, -1
            else:
                debit_account = account_obj.search([('code', '=', '2202'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                credit_account = self.payment_account_id
                debit_sign, credit_sign = 1, -1
        elif model == 'advance':
            if payment_type == 'inbound':
                debit_account = account_obj.search([('code', '=', '2203'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                credit_account = account_obj.search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = 1, -1
            else:
                debit_account = account_obj.search([('code', '=', '1123'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                credit_account = account_obj.search([('code', '=', '2202'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = -1, 1
        elif model == 'diff':
            if payment_type == 'inbound':
                debit_account = self.diff_account_id
                credit_account = account_obj.search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = 1, -1
            else:
                debit_account = account_obj.search([('code', '=', '2202'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                credit_account = self.diff_account_id
                debit_sign, credit_sign = 1, -1
        elif model == 'bank':
            if payment_type == 'inbound':
                debit_account = self.bank_account_id
                credit_account = account_obj.search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = 1, -1
            else:
                raise Warning(u'采购付款不需要银行扣款')
                pass
        elif model == 'exchange':
            if payment_type == 'inbound':
                debit_account = self.exchange_account_id
                credit_account = account_obj.search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
                debit_sign, credit_sign = 1, -1
            else:
                raise Warning(u'采购付款不需要汇兑差异')
                debit_sign, credit_sign = -1, 1
        return (debit_account, credit_account, debit_sign, credit_sign)

    def _check_plan_invoice(self, account, sign):
        flag = False
        if self.payment_type == 'inbound' and account.code == '1122' and sign == -1:
            flag = True
        if self.payment_type == 'outbound' and account.code == '2202' and sign == 1:
            flag = True
        return flag

    def _make_move_line(self, move, line, currency, amount_currency, account, sign, date=None):
        date = date or self.date
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False, date=date)
        data = {
            'name': self.name,
            'move_id': move.id,
            'account_id': account.id,
            'currency_id': currency.id,
            'amount_currency': amount_currency * sign,
            'partner_id': self.partner_id.id,
            'journal_id': self.journal_id.id,
            'invoice_id': line.invoice_id.id,
            'new_payment_id': self.yjzy_payment_id.id,#akiny new
            'new_advance_payment_id':line.yjzy_payment_id.id,
            'gongsi_id': self.gongsi_id.id,
        }
        if account.code in ['2203']:
            data.update({'so_id': line.so_id.id})
        if account.code in ['1123']:
            data.update({'po_id': line.po_id.id})

        if self._check_plan_invoice(account, sign):
            data.update({'plan_invoice_id': line.invoice_id.id, })
        aml = aml_obj.create(data)
        aml._onchange_amount_currency()
        return aml

    def _make_move_payment(self):
        _logger.info('>>>>>>>>>>>> _make_move_payment')
        if self.line_ids.filtered(lambda x: x.amount_payment_org != 0):
            debit_account, credit_account, debit_sign, credit_sign = self._prepare_move_line_account('payment')
            move_payment = self.env['account.move'].create(self._prepare_account_move())
            for line in self.line_ids.filtered(lambda x: x.amount_payment_org > 0):
                currency, amount_currency = line.payment_currency_id, line.amount_payment_org
                self._make_move_line(move_payment, line, currency, amount_currency, debit_account, debit_sign,
                                     self.date)
                self._make_move_line(move_payment, line, currency, amount_currency, credit_account, credit_sign,
                                     self.date)
            self.move_ids |= move_payment
            return move_payment

    def _make_move_advance(self):
        _logger.info('>>>>>>>>>>>> _make_move_advance')
        if self.line_ids.filtered(lambda x: x.amount_advance_org != 0):
            debit_account, credit_account, debit_sign, credit_sign = self._prepare_move_line_account('advance')
            # print ('====', debit_account, credit_account, debit_sign, credit_sign)
            move_advance = self.env['account.move'].create(self._prepare_account_move())
            for line in self.line_ids.filtered(lambda x: x.amount_advance_org > 0):
                currency, amount_currency = line.invoice_currency_id, line.amount_advance_org
                self._make_move_line(move_advance, line, currency, amount_currency, debit_account, debit_sign,
                                     self.date)
                self._make_move_line(move_advance, line, currency, amount_currency, credit_account, credit_sign,
                                     self.date)
            self.move_ids |= move_advance
            return move_advance

    def _make_move_diff(self):
        _logger.info('>>>>>>>>>>>> _make_move_diff')
        if self.line_ids.filtered(lambda x: x.amount_diff_org != 0):
            debit_account, credit_account, debit_sign, credit_sign = self._prepare_move_line_account('diff')
            move_diff = self.env['account.move'].create(self._prepare_account_move())
            for line in self.line_ids.filtered(lambda x: x.amount_diff_org > 0):
                currency, amount_currency = line.payment_currency_id, line.amount_diff_org
                self._make_move_line(move_diff, line, currency, amount_currency, debit_account, debit_sign, self.date)
                self._make_move_line(move_diff, line, currency, amount_currency, credit_account, credit_sign, self.date)
            self.move_ids |= move_diff
            return move_diff

    def _make_move_bank(self):
        _logger.info('>>>>>>>>>>>> _make_move_bank')
        if self.line_ids.filtered(lambda x: x.amount_bank_org != 0):
            debit_account, credit_account, debit_sign, credit_sign = self._prepare_move_line_account('bank')
            move_bank = self.env['account.move'].create(self._prepare_account_move())
            for line in self.line_ids.filtered(lambda x: x.amount_bank_org > 0):
                currency, amount_currency = line.payment_currency_id, line.amount_bank_org
                self._make_move_line(move_bank, line, currency, amount_currency, debit_account, debit_sign, self.date)
                self._make_move_line(move_bank, line, currency, amount_currency, credit_account, credit_sign, self.date)
            self.move_ids |= move_bank
            return move_bank

    def _make_move_exchange(self):
        _logger.info('>>>>>>>>>>>> _make_move_exchange')
        if self.line_ids.filtered(lambda x: x.amount_exchange != 0):
            aml_obj = self.env['account.move.line'].with_context(check_move_validity=False, date=self.date)
            debit_account, credit_account, debit_sign, credit_sign = self._prepare_move_line_account('exchange')
            move_exchange = self.env['account.move'].create(self._prepare_account_move())
            for line in self.line_ids.filtered(lambda x: x.amount_exchange > 0):
                currency, amount_currency = line.currency_id, line.amount_exchange_org
                self._make_move_line(move_exchange, line, currency, amount_currency, debit_account, debit_sign,
                                     self.date)
                self._make_move_line(move_exchange, line, currency, amount_currency, credit_account, credit_sign,
                                     self.date)
            self.move_ids |= move_exchange
            return move_exchange

    def make_account_move(self):
        self.ensure_one()
        if not self.move_ids:
            self._make_move_advance()
            self._make_move_payment()
            self._make_move_diff()
            self._make_move_bank()
            self._make_move_exchange()
            # user the onchange function to write 'debit' ,'credit' value
            for line in self.move_ids.mapped('line_ids').with_context(check_move_validity=False):
                line._onchange_amount_currency()


            # 重新计算so的应付余额
            sale_orders = self.invoice_ids.mapped('invoice_line_ids').mapped('purchase_id').mapped('source_so_id')
            sale_orders.compute_po_residual()


        # return {
        #     'name': u'分录',
        #     'view_type': 'form',
        #     'view_mode': 'tree,form',
        #     'res_model': 'account.move',
        #     'type': 'ir.actions.act_window',
        #     'domain': [('id', 'in', [x.id for x in moves])],
        # }

    def _prepare_sale_invoice_line(self, inv):#参考
        self.ensure_one()
        dic_so_invl = {}
        for line in inv.invoice_line_ids:
            if line.sale_line_ids:
                so = line.sale_line_ids[0].order_id
                if so in dic_so_invl:
                    dic_so_invl[so] |= line
                else:
                    dic_so_invl[so] = line
        return dic_so_invl or False

    def _prepare_purchase_invoice_line(self, inv):
        self.ensure_one()
        dic_po_invl = {}
        for line in inv.invoice_line_ids:
            if line.purchase_id:
                po = line.purchase_id
                if po in dic_po_invl:
                    dic_po_invl[po] |= line
                else:
                    dic_po_invl[po] = line
        return dic_po_invl or False

    def make_lines(self):
        self.ensure_one()
        if not self.line_ids:
            if self.partner_type == 'customer':
                self._make_lines_so()
            if self.partner_type == 'supplier':
                self._make_lines_po()
                # if self.operation_wizard != '03':
                #     if self.hxd_type_new == '40':
                #         self.operation_wizard = '10'
                #     elif self.hxd_type_new == '30':
                #         self.operation_wizard = '25'

    #从应付-付款申请的预付弹窗认领，用这个
    def make_lines_new(self):
        self.ensure_one()
        if self.partner_type == 'customer':
            self._make_lines_so()
        if self.partner_type == 'supplier':
            self._make_lines_po()
            if self.hxd_type_new == '40':
                self.operation_wizard = '10'
            elif self.hxd_type_new == '30':
                self.operation_wizard = '25'

                # tree_view = self.env.ref('yjzy_extend.account_yfhxd_advance_tree_view_new').id
                # form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
                #
                # action = self.env.ref('yjzy_extend.action_yfhxd_all_new_1').read()[0]
                # ctx = {
                #        'advance_po_amount': 1,
                #       }  # 预付-应付
                #
                # action['views'] = [(form_view, 'form')]
                # action['res_id'] = self.id,
                # action['context'] = ctx
                # action['target'] = 'new'
                # print('ctx_222', ctx)
                # print('action', action)
                # return action
                form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
                return {
                    'name': '添加账单',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'account.reconcile.order',
                    'views': [(form_view, 'form')],
                    'res_id': self.id,
                    'target': 'new',
                    'type': 'ir.actions.act_window',
                    'context': {'advance_po_amount': 1,}
                }


    def _make_lines_po(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        line_ids = None
        self.line_ids = line_ids

        # if self.no_sopo:
        #     for invoice in self.invoice_ids:
        #         line_obj.create({
        #             'order_id': self.id,
        #             'invoice_id': invoice.id,
        #             'amount_invoice_so': invoice.amount_total,
        #         })
        # else:
        for invoice in self.invoice_ids:
            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
            else:
                for po, invlines in po_invlines.items():
                    line_obj.create({
                        'order_id': self.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })
    #826
        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
        yjzy_advance_payment_id = self.yjzy_advance_payment_id
        for i in self.line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual = i.advance_residual
            order = i.order_id

            k = invoice.id
            if k in so_po_dic:
                print('k', k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual'] += advance_residual
            else:
                print('k1', k)
                so_po_dic[k] = {
                    'invoice_id': invoice.id,
                    'amount_invoice_so': amount_invoice_so,
                    'advance_residual': advance_residual, }

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': self.id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual': data['advance_residual'],
                'yjzy_payment_id': yjzy_advance_payment_id.id
            })

    def _make_lines_so(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        line_ids = None
        self.line_ids = line_ids
        # if self.no_sopo:
        #     for invoice in self.invoice_ids:
        #         line_obj.create({
        #             'order_id': self.id,
        #             'invoice_id': invoice.id,
        #             'amount_invoice_so': invoice.amount_total,
        #         })
        # else:
        for invoice in self.invoice_ids:
            so_invlines = self._prepare_sale_invoice_line(invoice)
            if not so_invlines:
                line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
            else:
                for so, invlines in so_invlines.items():
                    line_obj.create({
                        'order_id': self.id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })

        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
        yjzy_advance_payment_id = self.yjzy_advance_payment_id
        for i in self.line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual2 = i.advance_residual2
            order = i.order_id

            k = invoice.id
            if k in so_po_dic:
                print('k',k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual2'] += advance_residual2
            else:
                print('k1', k)
                so_po_dic[k] = {
                                'invoice_id':invoice.id,
                                'amount_invoice_so': amount_invoice_so,
                                'advance_residual2': advance_residual2,}

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': self.id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'advance_residual2': data['advance_residual2'],
                'yjzy_payment_id': yjzy_advance_payment_id.id
            })

    def _make_lines_po_from_expense(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        line_ids = None
        self.line_ids = line_ids

        # if self.no_sopo:
        #     for invoice in self.invoice_ids:
        #         line_obj.create({
        #             'order_id': self.id,
        #             'invoice_id': invoice.id,
        #             'amount_invoice_so': invoice.amount_total,
        #         })
        # else:
        for invoice in self.invoice_ids:
            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                    'amount_payment_org': invoice.amount_total,
                })
            else:
                for po, invlines in po_invlines.items():
                    line_obj.create({
                        'order_id': self.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'amount_payment_org': sum([i.price_subtotal for i in invlines]),

                    })
        # 826
        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
        yjzy_advance_payment_id = self.yjzy_advance_payment_id
        for i in self.line_ids:
            invoice = i.invoice_id
            amount_invoice_so = i.amount_invoice_so
            advance_residual = i.advance_residual
            order = i.order_id

            k = invoice.id
            if k in so_po_dic:
                print('k', k)
                so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
                so_po_dic[k]['advance_residual'] += advance_residual
            else:
                print('k1', k)
                so_po_dic[k] = {
                    'invoice_id': invoice.id,
                    'amount_invoice_so': amount_invoice_so,
                    'advance_residual': advance_residual, }

        for kk, data in list(so_po_dic.items()):
            line_no = line_no_obj.create({
                'order_id': self.id,
                'invoice_id': data['invoice_id'],
                'amount_invoice_so': data['amount_invoice_so'],
                'amount_payment_org': data['amount_invoice_so'],
                'advance_residual': data['advance_residual'],
                'yjzy_payment_id': yjzy_advance_payment_id.id,

            })
            # print('>>', line)
    #826 拆分发票填写的金额到明细上
    def update_line_amount(self):
        for x in self.line_no_ids:
            invoice = x.invoice_id

            amount_payment_org = x.amount_payment_org
            amount_bank_org = x.amount_bank_org
            amount_diff_org = x.amount_diff_org

            line_ids = self.line_ids.filtered(lambda x: x.invoice_id == invoice)
            for line in line_ids:
                amount_invoice_so_proportion = line.amount_invoice_so_proportion
                line.amount_payment_org = amount_invoice_so_proportion * amount_payment_org
                line.amount_bank_org = amount_invoice_so_proportion * amount_bank_org
                line.amount_diff_org = amount_invoice_so_proportion * amount_diff_org

    #仅仅针对预收 已经加上对预付的处理
    def update_line_advance_amount(self):
        for one in self.line_no_ids:
            invoice = one.invoice_id
            yjzy_payment_id = one.yjzy_payment_id
            amount_advance_org = one.amount_advance_org
            line_ids = self.line_ids.filtered(lambda x: x.invoice_id == invoice)
            print('invoice',invoice)
            if amount_advance_org == 0:  # 我们是把明细行全部填上预付单，所以要加判断，
                for line in line_ids:
                    line.amount_advance_org = 0
                    line.yjzy_payment_id = False
                continue
            if yjzy_payment_id and self.sfk_type == 'yshxd':
                if yjzy_payment_id.so_id:
                    a=0
                    for line in line_ids:
                        if line.so_id == yjzy_payment_id.so_id:
                            line.yjzy_payment_id = yjzy_payment_id
                            line.amount_advance_org = amount_advance_org
                            a = 1
                    if a == 0:
                        raise Warning('预收认领单的销售合同和应收账单不匹配')
                else:
                    for line in line_ids:#如果预收没有对应那个销售合同，那么将这个预收的金额根据比例分配给各个销售合同
                        amount_invoice_so_proportion = line.amount_invoice_so_proportion #这一行的销售合同占这次出运的比例，如果
                        line.amount_advance_org = amount_advance_org*amount_invoice_so_proportion
                        line.yjzy_payment_id = yjzy_payment_id
            elif yjzy_payment_id and self.sfk_type == 'yfhxd':
                if yjzy_payment_id.po_id:
                    a=0
                    for line in line_ids:
                        if line.po_id == yjzy_payment_id.po_id:
                            line.yjzy_payment_id = yjzy_payment_id
                            line.amount_advance_org = amount_advance_org
                            a = 1
                    if a == 0:
                        raise Warning('预付认领单的销售合同和应付账单不匹配')
                else:
                    for line in line_ids:
                        amount_invoice_so_proportion = line.amount_invoice_so_proportion
                        print('amount_invoice_so_proportion', amount_invoice_so_proportion)
                        line.amount_advance_org = amount_advance_org*amount_invoice_so_proportion
                        line.yjzy_payment_id = yjzy_payment_id





        # amount_advance_org = x.amount_advance_org
        # yjzy_payment_id = x.yjzy_payment_id
        # if yjzy_payment_id:
        #
        #         print('line.so_id', line.so_id, yjzy_payment_id.so_id)
        #         if line.so_id == yjzy_payment_id.so_id:
        #             line.yjzy_payment_id = yjzy_payment_id
        #             line.amount_advance_org = amount_advance_org
        #         else:
        #             raise Warning('预收单的订单和应收明细订单不匹配！')
        #     else:
        #         if amount_advance_org != 0:
        #             # line.amount_advance_org = amount_advance_org * amount_invoice_so_proportion
        #             line[0].amount_advance_org = amount_advance_org
        #             line[0].yjzy_payment_id = yjzy_payment_id  # 填入后，看是否生成一张付款单
        # else:
        #     # if amount_advance_org != 0:
        #     #     raise Warning('请填写预收认领单，或者设置预收认领金额为0!') #提交的时候判断
        #     line.amount_advance_org = 0
        #     line.yjzy_payment_id = False


    #akiny 828,将jinvoice_ids从o2m调整为m2m后，初始化一次
    def compute_invoice_ids(self):
        invoice = self.line_ids.mapped('invoice_id')
        self.invoice_ids = invoice

    def clear_moves(self):
        self.ensure_one()
        self.move_ids.write({'reconcile_order_id': False})
    #调整：lines要改成invoice或者将line_ids改成m2m
    def invoice_assign_outstanding_credit_new(self):
        self.ensure_one()
        # 没审核的分录不能核销
        for m in self.move_ids:
            if m.state == 'draft':
                raise Warning(u'分录 %s  %s 还没审核' % (m.id, m.state))

        lines = self.move_ids.mapped('line_ids')
        invoice = self.line_ids.mapped('invoice_id')
        print('invoice',invoice)
        for inv in invoice.filtered(lambda x: x.state == 'open'):
            print('inv', inv)
            # todo_lines = lines.filtered(lambda x: x.plan_invoice_id == inv and x.reconciled == False)
            todo_lines = invoice.filtered(lambda x: x.plan_invoice_id == inv and x.reconciled == False)
            for todo in todo_lines:
                inv.assign_outstanding_credit(todo.id)

    def invoice_assign_outstanding_credit(self):
        self.ensure_one()
        # 没审核的分录不能核销
        for m in self.move_ids:
            if m.state == 'draft':
                raise Warning(u'分录 %s  %s 还没审核' % (m.id, m.state))

        lines = self.move_ids.mapped('line_ids')
        for inv in self.invoice_ids.filtered(lambda x: x.state == 'open'):
            todo_lines = lines.filtered(lambda x: x.plan_invoice_id == inv and x.reconciled == False)
            for todo in todo_lines:
                inv.assign_outstanding_credit(todo.id)
                inv.bill_id.update_hexiao_state()

            # domain = [
            #     ('plan_invoice_id', '=', inv.id),
            #     ('account_id', '=', inv.account_id.id),
            #     ('partner_id', '=', self.env['res.partner']._find_accounting_partner(inv.partner_id).id),
            #     ('reconciled', '=', False), '|', ('amount_residual', '!=', 0.0), ('amount_residual_currency', '!=', 0.0)
            # ]
            # if inv.type in ('out_invoice', 'in_refund'):
            #     domain.extend([('credit', '>', 0), ('debit', '=', 0)])
            # else:
            #     domain.extend([('credit', '=', 0), ('debit', '>', 0)])

    def make_done(self):
        self.ensure_one()
        self.make_account_move()
        moves = self.move_ids
        moves.post()
        self.invoice_assign_outstanding_credit()
        # self.line_ids.yjzy_payment_id.compute_advance_balance_total()
        # print('test',self.line_ids.yjzy_payment_id.)
        self.state = 'done'
        return True

    def action_Warning(self):
        if self.partner_id.state != 'done':
            war = '客户正在审批中，请先完成客户的审批'
            raise Warning(war)

class account_reconcile_order_line(models.Model):
    _name = 'account.reconcile.order.line'

    def compute_info(self):
        for one in self:
            date = one.order_id.date
            invoice_currency = one.invoice_currency_id.with_context(date=date)
            bank_currency = one.payment_currency_id.with_context(date=date)
            diff_currency = one.payment_currency_id.with_context(date=date)
            payment_currency = one.payment_currency_id.with_context(date=date)
            company_currency = one.currency_id.with_context(date=date)
            ###
            one.advance_residual = one.so_id.balance
            one.advance_residual2 = one.po_id.balance

            one.amount_advance = invoice_currency.compute(one.amount_advance_org, company_currency)
            one.amount_payment = payment_currency.compute(one.amount_payment_org, company_currency)
            one.amount_bank = bank_currency.compute(one.amount_bank_org, company_currency)
            one.amount_diff = diff_currency.compute(one.amount_diff_org, company_currency)
            print('payment_currency',payment_currency)
            # one.amount_exchange = invoice_currency.compute(one.amount_exchange_org, company_currency)
            ###
            amount_total_org = one.amount_advance_org
            print('test--reconcile',amount_total_org)
            if payment_currency and invoice_currency:
                amount_total_org += payment_currency.compute(one.amount_payment_org, invoice_currency)
            if bank_currency and invoice_currency:
                amount_total_org += bank_currency.compute(one.amount_bank_org, invoice_currency)
            if diff_currency and invoice_currency:
                amount_total_org += diff_currency.compute(one.amount_diff_org, invoice_currency)


            # if one.yjzy_payment_id:
            #     one.yjzy_currency_id = one.yjzy_payment_id.currency_id
            # else:
            #     one.yjzy_currency_id = one.invoice_currency_id

            one.amount_total_org = amount_total_org

            # print('=payment_currency%s==invoice_currency%s==bank_currency%s==diff_currency%s=' % (payment_currency, invoice_currency, bank_currency, diff_currency) )
            # if all([payment_currency, invoice_currency, bank_currency, diff_currency]):
            #     one.amount_total_org = one.amount_advance_org + payment_currency.compute(one.amount_payment_org,
            #                                                                              invoice_currency) \
            #                            + bank_currency.compute(one.amount_bank_org, invoice_currency) \
            #                            + diff_currency.compute(one.amount_diff_org, invoice_currency)
            # else:
            #     one.amount_total_org = 0


            one.amount_total = one.amount_advance + one.amount_payment + one.amount_bank + one.amount_diff

    def _get_default_currency_id(self):
        return self.invoice_currency_id

    def _compute_amount_invoice_so_proportion(self):
        for one in self:
            amount_invoice = one.invoice_id.amount_total
            amount_invoice_so =  one.amount_invoice_so
            residual = one.residual
            if amount_invoice !=0:
                amount_invoice_so_proportion = amount_invoice_so / amount_invoice
            else:
                amount_invoice_so_proportion = 0
            amount_invoice_so_residual = residual * amount_invoice_so_proportion
            print('amount_invoice_so_residual',amount_invoice_so,amount_invoice_so_residual,amount_invoice_so_proportion)
            one.amount_invoice_so_proportion = amount_invoice_so_proportion
            one.amount_invoice_so_residual = amount_invoice_so_residual



    @api.depends('yjzy_payment_id','payment_currency_id','yjzy_payment_id.currency_id')
    def _compute_yjzy_currency_id(self):
        for one in self:
            if not one.yjzy_payment_id:
                one.yjzy_currency_id = one.payment_currency_id
            else:
                one.yjzy_currency_id = one.yjzy_payment_id.currency_id


    # @api.onchange('amount_invoice_so', 'amount_advance_org', 'amount_bank_org', 'amount_diff_org', 'amount_payment_org')
    # def onchange_amount(self):
    #     self.amount_exchange_org = self.amount_invoice_so - self.amount_advance_org - self.amount_bank_org - self.amount_diff_org - self.amount_payment_org

    date = fields.Date('日期',related="order_id.date")
    order_id = fields.Many2one('account.reconcile.order', u'核销单')
    partner_type = fields.Selection(related='order_id.partner_type')
    payment_type = fields.Selection(related='order_id.payment_type')

    so_id = fields.Many2one('sale.order', u'销售单')
    so_contract_code = fields.Char(u'销售合同号', related='so_id.contract_code', readonly=True)

    invoice_display_name =  fields.Char('发票显示名字', related='invoice_id.display_name' , store=True)


    po_id = fields.Many2one('purchase.order', u'采购单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    tb_contract_code = fields.Char('出运合同号', related='invoice_id.tb_contract_code', readonly=True)
    residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True, currency_field='invoice_currency_id')
    currency_id = fields.Many2one('res.currency', u'公司货币', related='order_id.currency_id', readonly=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='order_id.payment_currency_id', readonly=True)

    ##银行扣款和销售费用的货币随收款货币；
    # bank_currency_id = fields.Many2one('res.currency', related='order_id.bank_currency_id', )
    # diff_currency_id = fields.Many2one('res.currency', related='order_id.diff_currency_id', )

    amount_invoice_so = fields.Monetary(u'合计', currency_field='invoice_currency_id')
    amount_invoice_so_proportion = fields.Float('销售金额占发票金额比',compute=_compute_amount_invoice_so_proportion)
    #826
    amount_invoice_so_residual = fields.Monetary(u'剩余',currency_field='invoice_currency_id',compute=_compute_amount_invoice_so_proportion)

    advance_residual = fields.Monetary(currency_field='yjzy_currency_id', string=u'预付余额', compute=compute_info, )
    advance_residual2 = fields.Monetary(currency_field='yjzy_currency_id', string=u'预收余额', compute=compute_info, )

    advance_account_id = fields.Many2one(related='so_id.advance_account_id', string='预收账户')
    company_id =  fields.Many2one('res.company', string=u'公司', related='order_id.company_id')
   # yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单', related='so_id.yjzy_payment_id')
    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单')
    yjzy_payment_display_name = fields.Char('显示名称',related='yjzy_payment_id.display_name',store=True)
    #yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_id.currency_id')
    # yjzy_currency_id = fields.Many2one('res.currency', u'预收币种',default=lambda self: self.env.user.company_id.currency_id.id)
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种',compute=_compute_yjzy_currency_id)
    amount_advance_org = fields.Monetary(u'预收金额', currency_field='yjzy_currency_id')

    amount_advance = fields.Monetary(u'预收金额:本币', currency_field='currency_id', compute=compute_info)
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='payment_currency_id')
    amount_payment = fields.Monetary(u'收款金额:本币', currency_field='currency_id', compute=compute_info)
    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='invoice_currency_id')
    amount_bank = fields.Monetary(u'银行扣款:本币', currency_field='currency_id', compute=compute_info)
    amount_diff_org = fields.Monetary(u'销售费用', currency_field='invoice_currency_id')
    amount_diff = fields.Monetary(u'销售费用:本币', currency_field='currency_id', compute=compute_info)
    amount_exchange_org = fields.Monetary(u'汇兑差异', currency_field='invoice_currency_id')
    amount_exchange = fields.Monetary(u'汇兑差异:本币', currency_field='currency_id')
    amount_total_org = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_info)
    amount_total = fields.Monetary(u'收款合计:本币', currency_field='currency_id', compute=compute_info)

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment_id(self):
        print('yjzy_currency_id',self.yjzy_currency_id)
        self.yjzy_currency_id = self.yjzy_payment_id.currency_id


class account_reconcile_order_line_no(models.Model):
    _name = 'account.reconcile.order.line.no'



    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    order_id = fields.Many2one('account.reconcile.order', u'核销单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    invoice_id_po_ids = fields.Many2many('purchase.order',related='invoice_id.po_ids')

    invoice_residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True, currency_field='invoice_currency_id')
    invoice_attribute = fields.Selection(related='invoice_id.invoice_attribute',string=u'账单类型')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种',
                                       default=lambda self: self.env.user.company_id.currency_id.id)
    payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='order_id.payment_currency_id',
                                          readonly=True)
    currency_id = fields.Many2one('res.currency', u'公司货币', related='order_id.currency_id', readonly=True)
    amount_invoice_so = fields.Monetary(u'合计', currency_field='invoice_currency_id')
    amount_invoice_so_residual = fields.Monetary(u'剩余', currency_field='invoice_currency_id')
    advance_residual = fields.Monetary(currency_field='yjzy_currency_id', string=u'预付余额')
    advance_residual2 = fields.Monetary(currency_field='yjzy_currency_id', string=u'预收余额')
    residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True, currency_field='invoice_currency_id')

    amount_advance_org = fields.Monetary(u'预收金额', currency_field='yjzy_currency_id')
    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单')
    yjzy_payment_po_id = fields.Many2one('purchase.order',related='yjzy_payment_id.po_id',string='预付采购')

    amount_advance = fields.Monetary(u'预收金额:本币', currency_field='currency_id' )
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='payment_currency_id')
    amount_payment = fields.Monetary(u'收款金额:本币', currency_field='currency_id', )

    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='payment_currency_id')
    amount_diff_org = fields.Monetary(u'订单费用', currency_field='payment_currency_id')




