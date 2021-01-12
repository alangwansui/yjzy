# -*- coding: utf-8 -*-
from odoo import models, tools,  fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from .comm import sfk_type, invoice_attribute_all_in_one
import logging

_logger = logging.getLogger(__name__)
#注意：直接单独创建应付申请，和预付认领的时候，默认状态需要注意
Account_reconcile_Selection =   [('draft',u'待预付认领草稿'),
                                 ('draft_yshxd',u'待预收认领草稿'),
                                 ('draft_all',u'待认领草稿'),#同时认领
                                 ('advance_approval',u'预付款认领待审批'),
                                 ('advance_approval_yshxd',u'预收款认领待审批'),
                                 ('account_approval',u'应付款申请草稿'),
                                 ('account_approval_yshxd',u'应收款认领草稿'),
                                 ('manager_approval',u'应付款申请待审批'),
                                 ('manager_approval_yshxd',u'应收款认领待审批'),
                                 ('manager_approval_all',u'认领待审批'),
                                 ('post',u'审批完成待付款-未提交'),
                                 ('fkzl',u'审批完成待付款-已提交'),
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
                    one.payment_currency_id = one.invoice_currency_id#注意
                else:
                    one.payment_currency_id = one.fk_journal_id.currency_id
            elif one.sfk_type == 'yshxd':
                if not one.yjzy_payment_id:
                    one.payment_currency_id = one.invoice_currency_id
                else:
                    one.payment_currency_id = one.yjzy_payment_id.currency_id
            else:
                one.payment_currency_id = one.yjzy_payment_id.currency_id

    @api.depends('line_ids','line_ids.advance_residual','line_ids.advance_residual2')
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
            # if not one.line_ids:
            #     continue
            invoices = one.line_ids.mapped('invoice_id')
            if len(one.invoice_ids.mapped('currency_id')) > 1:
                raise Warning('选择的发票的交易货币不一致')

            if one.line_ids:
                invoice_currency = one.line_ids[0].invoice_currency_id
            elif one.line_no_ids:
                invoice_currency = one.line_no_ids[0].invoice_currency_id
            else:
                invoice_currency = one.currency_id
            #<jon>

            company_currency = one.currency_id
            one.invoice_currency_id = invoice_currency
            one.amount_invoice_residual_org = sum([x.residual for x in invoices])
            one.amount_invoice_org = sum([x.amount_total for x in invoices])
            one.amount_invoice = sum(
                [invoice_currency.with_context(date=x.date_invoice).compute(x.residual, company_currency) for x in
                 invoices])

    @api.depends('fk_journal_id')
    def compute_by_lines(self):
        for one in self:
            date = one.date
            if (not one.line_ids and not one.line_no_ids) or (not one.payment_currency_id):
                continue
            bank_currency = one.payment_currency_id.with_context(date=date)
            diff_currency = one.payment_currency_id.with_context(date=date)
            payment_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids
            lines_no = one.line_no_ids

            one.amount_advance_org = sum([x.amount_advance_org for x in lines]) #预收预付认领总计
            one.amount_advance = sum([x.amount_advance for x in lines])
            one.amount_bank_org = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]),one.invoice_currency_id)
            one.amount_bank = sum([x.amount_bank for x in lines])
            one.amount_diff_org = diff_currency.compute(sum([x.amount_diff_org for x in lines]),one.invoice_currency_id)
            one.amount_diff = sum([x.amount_diff for x in lines])
            one.amount_payment_org = payment_currency.compute(sum([x.amount_payment_org for x in lines])+sum([x.amount_payment_org for x in lines_no]),
                                                              one.invoice_currency_id)
            one.amount_payment = sum([x.amount_payment for x in lines])
            one.amount_total_org = sum([x.amount_total_org for x in lines]) + sum([x.amount_payment_org for x in lines_no])
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
    def compute_supplier_advance_payment_ids(self):#字段用作预收和预付一起
        for one in self:
            po = []
            if one.sfk_type == 'yfhxd':
                for x in one.invoice_ids:
                    for line in x.invoice_line_ids.mapped('purchase_id'):
                        po.append(line.id)
                    po.append(False)                #

                print('po_akiny',po)
                supplier_advance_payment_ids = self.env['account.payment'].search(
                    [('company_id','=',self.env.user.company_id.id),('partner_id', '=', one.partner_id.id), ('sfk_type', '=', 'yfsqd'),('po_id','in',po),
                     ('state', 'in', ['posted', 'reconciled']),('advance_balance_total','!=',0)])
            else:
                for x in one.invoice_ids:
                    for line in x.invoice_line_ids.mapped('so_id'):
                        po.append(line.id)
                    po.append(False)  #
                print('po', po)
                supplier_advance_payment_ids = self.env['account.payment'].search(
                    [('company_id','=',self.env.user.company_id.id),('partner_id', '=', one.partner_id.id), ('sfk_type', '=', 'ysrld'), ('so_id', 'in', po),
                     ('state', 'in', ['posted', 'reconciled']), ('advance_balance_total', '!=', 0)])
            one.supplier_advance_payment_ids_count = len(supplier_advance_payment_ids)
            one.supplier_advance_payment_ids = supplier_advance_payment_ids
            print('one.supplier_advance_payment_ids',one.supplier_advance_payment_ids)
        # self.write({'supplier_advance_payment_ids': [line.id for line in supplier_advance_payment_ids]})

    @api.depends('line_ids','line_ids.amount_advance_org','line_no_ids','state_1')
    def compute_amount_advance_org_new(self):
        for one in self:
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            lines = one.line_ids
            lines_no = one.line_no_ids
            one.amount_advance_org_new = sum([x.amount_advance_org for x in lines])

    @api.depends('line_ids', 'line_ids.amount_payment_org','payment_currency_id','line_no_ids','line_no_ids.amount_payment_org')
    def compute_amount_payment_org_new(self):
        for one in self:
            date = one.date
            if (not one.line_ids and not one.line_no_ids) or (not one.payment_currency_id):
                continue
            payment_currency = one.payment_currency_id.with_context(date=date)
            lines = one.line_ids
            lines_no = one.line_no_ids
            amount_payment_org = sum([x.amount_payment_org for x in lines]) + sum([x.amount_payment_org for x in lines_no])
            one.amount_payment_org_new = payment_currency.compute(amount_payment_org,
                                                              one.invoice_currency_id)
            print('amount_payment_org_new_akiny',one.amount_payment_org_new)



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

    @api.depends('line_ids', 'line_ids.amount_total_org_new','line_ids.amount_advance_org','line_ids.amount_payment_org','line_no_ids',
                 'line_no_ids.amount_payment_org','line_no_ids.amount_total_org','payment_currency_id')
    def compute_amount_total_org_new(self):
        for one in self:
            if (not one.line_ids and not one.line_no_ids) or (not one.payment_currency_id):
                continue
            lines = one.line_ids
            lines_no = one.line_no_ids
            amount_line_no = sum(x.amount_total_org for x in lines_no)
            amount_line = sum(x.amount_payment_org for x in lines)
            one.amount_total_org_new = amount_line_no + amount_line
            print('amount_total_org_new',one.amount_total_org_new)
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

    @api.depends('stage_id','invoice_ids','supplier_advance_payment_ids')
    def compute_supplier_advance_payment_ids_amount_advance_org(self):
        for one in self:
            supplier_advance_payment_ids_amount_advance_org = sum(x.advance_reconcile_order_draft_amount_advance for x in one.supplier_advance_payment_ids)
            one.supplier_advance_payment_ids_amount_advance_org = supplier_advance_payment_ids_amount_advance_org

    @api.depends('line_no_ids','line_no_ids.advice_amount_advance_org','line_no_ids.least_advice_amount_advance_org')
    def compute_advice_amount_advance_org_total(self):
        for one in self:
            advice_amount_advance_org_total = sum(x.advice_amount_advance_org for x in one.line_no_ids)
            least_advice_amount_advance_org = sum(x.least_advice_amount_advance_org for x in one.line_no_ids)
            one.advice_amount_advance_org_total = advice_amount_advance_org_total
            one.least_advice_amount_advance_org = least_advice_amount_advance_org

    # @api.depends('yjzy_payment_id','yjzy_payment_id.balance')
    # def compute_yjzy_payment_balance(self):
    #     for one in self:
    #         one.yjzy_payment_balance = one.yjzy_payment_id.balance

    #其他应收认领的时候，一个快速添加金额的字段，onchange到line_no_ids和line_ids的第一行
    # other_payment_amount_payment_org = fields.Monetary(u'其他应收认领快速录入金额')
    # other

    @api.depends('yjzy_advance_payment_id','yjzy_advance_payment_id.amount_advance_org_all','yjzy_advance_payment_id.advice_amount_advance_org_all')
    def compute_ysrld_amount_advance_org_all(self):
        for one in self:
            ysrld_amount_advance_org_all =  one.yjzy_advance_payment_id.amount_advance_org_all
            ysrld_advice_amount_advance_org_all = one.yjzy_advance_payment_id.advice_amount_advance_org_all
            duoyu_this_time_advice_advance_org = ysrld_advice_amount_advance_org_all - ysrld_amount_advance_org_all
            print('duoyu_this_time_advice_advance_org', duoyu_this_time_advice_advance_org)
            one.ysrld_amount_advance_org_all = ysrld_amount_advance_org_all
            one.ysrld_advice_amount_advance_org_all = ysrld_advice_amount_advance_org_all
            one.duoyu_this_time_advice_advance_org = duoyu_this_time_advice_advance_org

    # def compute_yjzy_reconcile_order_ids_count(self):
    #     for one in self:
    #         yjzy_reconcile_order_ids_count = len(one.yjzy_reconcile_order_ids)
    #         one.yjzy_reconcile_order_ids_count = yjzy_reconcile_order_ids_count

    @api.depends('line_no_ids','line_no_ids.invoice_id','line_no_ids.invoice_amount_total')
    def compute_by_invoice_line_ids(self):
        for one in self:
            amount_invoice_org_new = sum(x.invoice_amount_total for x in one.line_no_ids)
            one.amount_invoice_org_new = amount_invoice_org_new

    @api.depends('partner_id','partner_id.supplier_amount_invoice_approval','partner_id.supplier_amount_invoice_approve',
                 'partner_id.supplier_amount_residual_invoice','partner_id.supplier_advance_amount_hxd_line_approval')
    def compute_supplier_amount_invoice_approve_approval(self):
        for one in self:
            supplier_invoice_ids = one.partner_id.supplier_invoice_ids.filtered(lambda x: x.company_id  == self.env.user.company_id)
            supplier_advance_payment_ids = one.partner_id.supplier_advance_payment_ids.filtered(lambda x: x.company_id  == self.env.user.company_id)

            supplier_amount_invoice_approval = sum(x.amount_payment_approval_all for x in supplier_invoice_ids)
            supplier_amount_invoice_approve = sum(x.amount_payment_approve_all for x in supplier_invoice_ids)
            supplier_amount_invoice_residual = sum(x.residual_signed for x in supplier_invoice_ids)
            supplier_advance_amount_hxd_line_approval = sum(x.advance_amount_reconcile_order_line_approval for x in supplier_advance_payment_ids)
            supplier_amount_residual_advance_payment = sum(x.advance_balance_total for x in supplier_advance_payment_ids)

            supplier_amount_invoice_residual2 = supplier_amount_invoice_residual - supplier_amount_invoice_approval - supplier_amount_invoice_approve
            supplier_advance_amount_hxd_line_approval2 = supplier_amount_residual_advance_payment - supplier_advance_amount_hxd_line_approval
            one.supplier_amount_invoice_approval = supplier_amount_invoice_approval
            one.supplier_amount_invoice_approve = supplier_amount_invoice_approve
            one.supplier_amount_invoice_residual = supplier_amount_invoice_residual
            one.supplier_amount_invoice_residual2 = supplier_amount_invoice_residual2
            one.supplier_advance_amount_hxd_line_approval = supplier_advance_amount_hxd_line_approval
            one.supplier_advance_amount_hxd_line_approval2 = supplier_advance_amount_hxd_line_approval2

    @api.depends('account_payment_state_ids','account_payment_state_ids.amount_advance_balance_d','account_payment_state_ids.amount_reconcile',
                 'account_payment_state_ids.amount_advance_balance_after',)
    def compute_account_payment_state_ids(self):
        for one in self:
            account_payment_state_ids = one.account_payment_state_ids
            one.account_payment_state_ids_amount_1 = sum(x.amount_advance_balance_d for x in account_payment_state_ids)
            one.account_payment_state_ids_amount_2 = sum(x.amount_advance_balance_after for x in account_payment_state_ids)
            one.account_payment_state_ids_amount_3 = sum(x.amount_reconcile for x in account_payment_state_ids)

    @api.depends('partner_id.supplier_amount_advance_payment','partner_id','partner_id.supplier_amount_residual_advance_payment')
    def compute_supplier_amount_residual_advance_payment(self):
        for one in self:
            supplier_advance_payment_ids = one.partner_id.supplier_advance_payment_ids.filtered(
                lambda x: x.company_id == self.env.user.company_id)

            one.supplier_amount_residual_advance_payment = sum(x.advance_balance_total for x in supplier_advance_payment_ids)
            one.supplier_amount_advance_payment = sum(x.amount for x in supplier_advance_payment_ids)

    # yingfurld_ids = fields.One2many('account.payment','account_reconcile_order_id','应付认领单')

    # @api.depends('line_no_ids')
    # def compute_line_no_compute_ids(self):
    #     for one in self:
    #         one.line_no_compute_ids = one.line_no_ids

    @api.depends('line_no_ids','line_no_ids.amount_payment_can_approve_all_after')
    def compute_amount_payment_can_approve_all_after(self):
        for one in self:
            one.amount_payment_can_approve_all_after = sum(x.amount_payment_can_approve_all_after for x in one.line_no_ids)

    # @api.depends('line_ids.yjzy_payment_id')
    # def compute_line_do_ids(self):
    #     line_ids = self.env['account.reconcile.order.line'].search([('yjzy_payment_id','!=',False),('order_id','=',self.id)])
    #     # line_ids = self.line_ids.filtered(lambda x: x.yjzy_payment_id != False)
    #     print('line_ids_akiny_do',line_ids)
    #     self.line_do_ids = line_ids

    def compute_payment_term_id(self):
        for one in self:
            if one.partner_id.customer == True and one.partner_id.supplier == False:
                one.partner_payment_term_id = one.partner_id.property_payment_term_id
            if one.partner_id.supplier == True and one.partner_id.customer == False:
                one.partner_payment_term_id = one.partner_id.property_supplier_payment_term_id
            if one.invoice_ids:
                one.invoice_payment_term_id = one.invoice_ids[0].payment_term_id

    @api.depends('invoice_ids')
    def compute_invoice_id(self):
        for one in self:
            if one.invoice_ids:
                invoice_id = one.invoice_ids[0]
                one.invoice_id = invoice_id
                one.invoice_attribute_all_in_one = invoice_id.invoice_attribute_all_in_one
                one.payment_log_ids = invoice_id.payment_log_ids

    @api.depends('invoice_ids')
    def compute_move_line_com_ids(self):
        for one in self:
            one.move_line_com_yfzk_ids = one.invoice_id.move_line_com_yfzk_ids
            one.move_line_com_yszk_ids = one.invoice_id.move_line_com_yszk_ids
            one.reconcile_order_ids = one.invoice_id.reconcile_order_ids
            one.reconcile_order_ids_count = one.invoice_id.reconcile_order_ids_count
            one.move_line_com_yszk_ids_count = one.invoice_id.move_line_com_yszk_ids_count
            one.move_line_com_yfzk_ids_count = one.invoice_id.move_line_com_yfzk_ids_count

    @api.depends('name')
    def compute_display_name(self):
        ctx = self.env.context
        res = []
        for one in self:
            if one.invoice_attribute_all_in_one == '410':
                name = '%s:%s' % ('其他应收认领',one.name)
            elif one.invoice_attribute_all_in_one == '110':
                name = '%s:%s' % ('主账单应收认领',one.name)
            elif one.invoice_attribute_all_in_one == '120':
                name = '%s:%s' % ('主账单应付申请',one.name)
            elif one.invoice_attribute_all_in_one == '130':
                name = '%s:%s' % ('主账单退税认领',one.name)
            elif one.invoice_attribute_all_in_one == '210':
                name = '%s:%s' % ('增加采购应收认领',one.name)
            elif one.invoice_attribute_all_in_one == '220':
                name = '%s:%s' % ('增加采购应付申请',one.name)
            elif one.invoice_attribute_all_in_one == '230':
                name = '%s:%s' % ('增加采购退税认领',one.name)
            elif one.invoice_attribute_all_in_one == '310':
                name = '%s:%s' % ('费用转货款应收认领',one.name)
            elif one.invoice_attribute_all_in_one == '320':
                name = '%s:%s' % ('费用转货款应付申请',one.name)
            elif one.invoice_attribute_all_in_one == '340':
                name = '%s:%s' % ('费用转货款退税认领',one.name)
            else:
                # one.invoice_attribute_all_in_one == '510':
                name = '%s:%s' % ('其他应付',one.name)

            one.display_name = name

    def compute_account_payment_state_ids_count(self):
        for one in self:
            one.account_payment_state_ids_count =len(one.account_payment_state_ids)


    invoice_reconcile_order_line_no_ids = fields.One2many('account.reconcile.order.line.no', related='invoice_id.reconcile_order_line_no_ids')
    invoice_reconcile_order_line_no_ids_count = fields.Integer(u'no数量',related='invoice_id.reconcile_order_line_no_ids_count')


    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    move_line_com_yfzk_ids = fields.Many2many('account.move.line.com',  u'发票相关应付账款分录',compute=compute_move_line_com_ids)
    move_line_com_yszk_ids = fields.Many2many('account.move.line.com', u'发票相关应付账款分录', compute=compute_move_line_com_ids)

    reconcile_order_ids = fields.Many2many('account.reconcile.order',compute=compute_move_line_com_ids)
    reconcile_order_ids_count = fields.Integer(u'核销单据数量', compute=compute_move_line_com_ids)

    move_line_com_yszk_ids_count = fields.Integer('应收日志数量', compute=compute_move_line_com_ids)
    move_line_com_yfzk_ids_count = fields.Integer('应付日志数量', compute=compute_move_line_com_ids)

    payment_log_ids = fields.One2many('account.payment',compute=compute_move_line_com_ids)

    invoice_id = fields.Many2one('account.invoice',compute=compute_invoice_id)
    # invoice_attribute_all_in_one = fields.Char('账单属性all_in_one',compute=compute_invoice_id)
    #
    invoice_attribute_all_in_one = fields.Selection(invoice_attribute_all_in_one,u'账单属性all_in_one', compute=compute_invoice_id)

    partner_payment_term_id = fields.Many2one('account.payment.term',u'伙伴付款条款',compute=compute_payment_term_id)
    invoice_payment_term_id = fields.Many2one('account.payment.term',u'合同付款条款',compute=compute_payment_term_id)

    amount_payment_can_approve_all_after = fields.Monetary('所有账单本次申请后可申请支付金额合计',currency_field='invoice_currency_id' , compute=compute_amount_payment_can_approve_all_after)

    account_payment_state_ids_amount_1 = fields.Float('预收本次认领前金额',compute=compute_account_payment_state_ids)
    account_payment_state_ids_amount_2 = fields.Float('预收本次认领后金额', compute=compute_account_payment_state_ids)
    account_payment_state_ids_amount_3 = fields.Float('预收本次金额', compute=compute_account_payment_state_ids)


    account_payment_state_ids = fields.One2many('account.payment.state','reconcile_order_id')
    account_payment_state_ids_count = fields.Integer('预收单数量',compute=compute_account_payment_state_ids_count)

    ysrld_amount_advance_org_all = fields.Float('预收单的本所有被认领金额',compute=compute_ysrld_amount_advance_org_all,store=True)
    ysrld_advice_amount_advance_org_all = fields.Float('预收认领单的所有被认领的原则分配金额',compute=compute_ysrld_amount_advance_org_all,store=True)
    duoyu_this_time_advice_advance_org = fields.Float('多余的预收付这次应该加上的认领金额',compute=compute_ysrld_amount_advance_org_all,store=True)

    yjzy_reconcile_order_id_new = fields.Many2one('account.reconcile.order','关联的核销单') #1126先创建预付，再创建应付，两边同时相互记录,ondelete='cascade'

    advice_amount_advance_org_total = fields.Monetary(u'建议预收金额', currency_field='yjzy_advance_currency_id',compute=compute_advice_amount_advance_org_total,store=True)
    least_advice_amount_advance_org = fields.Monetary(u'最低预收预付金额', currency_field='yjzy_advance_currency_id',compute=compute_advice_amount_advance_org_total,store=True)
    #0104
    yjzy_reconcile_order_id = fields.Many2one('account.reconcile.order','关联的核销单')#从付款申请认领的时候，创建预付申请，让两者之间产生关联,ondelete='cascade'

    # yjzy_reconcile_order_ids = fields.One2many('account.reconcile.order','yjzy_reconcile_order_id','相关的核销单汇总')#从自身创建的所有的预付-应付认领单。
    # yjzy_reconcile_order_ids_count = fields.Integer('相关的核销单汇总数量',compute=compute_yjzy_reconcile_order_ids_count)

    yjzy_reconcile_order_approval_ids = fields.One2many('account.reconcile.order', 'yjzy_reconcile_order_id', u'相关待审批预付-应付认领',
                                                        domain=[('state_1','=','manager_approval')],
                                              )  # 从自身创建的所有的预付-应付认领单。

    renling_type = fields.Selection([('yshxd', '应收认领'),
                                     ('back_tax', '退税认领'), ('other_payment', '其他认领')], u'认领属性') #没有是指作用
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    back_tax_declaration_id = fields.Many2one('back.tax.declaration',u'退税申报表')
    declaration_amount_all = fields.Monetary(u'本次申报金额',
                                             related='back_tax_declaration_id.declaration_amount_all')
    declaration_amount_all_residual_new = fields.Monetary(u'本次申报金额',
                                                          related='back_tax_declaration_id.declaration_amount_all_residual_new')

    name_title = fields.Char(u'账单描述')
    invoice_partner = fields.Char(u'账单对象')

    supplier_advance_payment_ids_amount_advance_org = fields.Float('待审批预付认领金额',compute= compute_supplier_advance_payment_ids_amount_advance_org)
    supplier_amount_invoice_approval = fields.Float(u'已申请未审批',compute=compute_supplier_amount_invoice_approve_approval)
    supplier_amount_invoice_approve = fields.Float(u'已审批未付款',compute=compute_supplier_amount_invoice_approve_approval)
    supplier_amount_invoice_residual = fields.Float(u'供应商应付余额',compute=compute_supplier_amount_invoice_approve_approval)
    supplier_amount_invoice_residual2 = fields.Float(u'供应商应付余额2',
                                                    compute=compute_supplier_amount_invoice_approve_approval,
                                                    )

    supplier_advance_amount_hxd_line_approval= fields.Float(u'供应商预付审批中预付认领',compute=compute_supplier_amount_invoice_approve_approval)
    supplier_advance_amount_hxd_line_approval2 = fields.Float(u'供应商预付余额2',compute=compute_supplier_amount_invoice_approve_approval)
    yjzy_type = fields.Selection([('sale','销售'),
                                  ('purchase','采购'),
                                  ('back_tax','退税'),
                                  ('other_payment_sale','其他应收'),#等待删除
                                  ('other_payment_purchase','其他应付')#等待删除
                                  ],u'发票类型')
    invoice_attribute = fields.Selection(
        [('normal', u'常规账单'),
         ('reconcile', u'核销账单'),#等待删除
         ('extra', u'额外账单'),#等待删除
         ('other_po', u'直接增加'),
         ('expense_po', u'费用转换'),
         ('other_payment',u'其他')], '账单属性')

    invoice_type_main = fields.Selection([('10_main', u'常规账单'),
                                          ('20_extra', u'额外账单'),
                                          ('30_reconcile', u'核销账单')],'账单类型')

    stage_id = fields.Many2one(
        'account.reconcile.stage',
        default=_default_account_reconcile_stage,copy=False)
    state_1 = fields.Selection(Account_reconcile_Selection, u'审批流程', default='draft', index=True, related='stage_id.state',
                               track_visibility='onchange')  # 费用审批流程
    #0911
    #核销单分预收付-应收付，应收付-收付款
    hxd_type_new = fields.Selection([('10', u'预收认领'),
                                     ('20', u'收款认领'),
                                     ('25',u'同时认领'),
                                     ('30', u'预付-应付'),
                                     ('40', u'应付-付款'),
                                     ('45', u'同时付'),
                                     ('50', u'核销-应收'),
                                     ('60', u'核销-应付')],'认领来源')
    # 827
    operation_wizard = fields.Selection([('03', u'预收付前置'),
                                         ('05', u'创建明细行'),#
                                         ('10', u'收付认领'),
                                         ('20', u'预收认领'),
                                         ('25', u'预收简易认领'),#
                                         ('30', u'同时认领'),#
                                         ('40', u'核销')], '认领方式')  # 决定视图上预收付认领还是收付款申请，引用line_no_ids或者line_ids
    #908
    # supplier_advance_payment_ids_char = fields.Char(u'相关预付',compute=_compute_supplier_advance_payment_ids_char)

    advance_reconcile_line_draft_all_count = fields.Integer('未完成审批的预付认领单数量',compute=compute_advance_reconcile_line_draft_all_count)

    expense_sheet_id = fields.Many2one('hr.expense.sheet',u'费用报告')
    supplier_advance_payment_ids = fields.Many2many('account.payment',u'相关预收付', compute=compute_supplier_advance_payment_ids) #相关的预收和预付
    supplier_advance_payment_ids_count = fields.Integer('相关预付数量',compute=compute_supplier_advance_payment_ids)
    #903
    reconcile_payment_ids = fields.One2many('account.payment','account_reconcile_order_id',u'认领单')
    yjzy_advance_payment_id = fields.Many2one('account.payment',u'预收认领单')#从预收认领单创建过滤用
    yjzy_advance_currency_id = fields.Many2one('res.currency','预收付款单货币',related='yjzy_advance_payment_id.currency_id')
    yjzy_advance_payment_balance = fields.Monetary('预付款单余额',currency_field='yjzy_advance_currency_id', related='yjzy_advance_payment_id.advance_balance_total')
    yjzy_advance_payment_amount = fields.Monetary('预付款单原始金额', currency_field='yjzy_advance_currency_id', related='yjzy_advance_payment_id.amount')
    # yjzy_advance_payment_approve_balance = fields.Monetary('预付款单余额',currency_field='yjzy_advance_currency_id', related='yjzy_advance_payment_id.approve_balance')

    #0901
    approve_date = fields.Date(u'审批完成时间')
    approve_uid = fields.Many2one('res.users',u'审批人')

    #828
    comments = fields.Text('备注')

    reconcile_type = fields.Selection([('normal',u'正常阶段'),('un_normal',u'核销阶段')],string=u'阶段', default='normal')
    name = fields.Char(u'编号', default=lambda self: self._default_name())
    payment_type = fields.Selection([('outbound', u'付款'), ('inbound', u'收款'), ('claim_in', u'收款认领'), ('claim_out', u'付款认领')], string=u'收/付款',
                                    required=True)
    partner_type = fields.Selection([('customer', u'客户'), ('supplier', u'供应商')], string=u'伙伴类型', )
    journal_id = fields.Many2one('account.journal', u'日记账', required=True, default=lambda self: self.default_journal())
    company_id = fields.Many2one('res.company', string=u'公司', required=True, default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', u'合作伙伴', required=True)

    amount_purchase_advance = fields.Monetary('预付金额:本币', currency_field='currency_id',related='partner_id.amount_purchase_advance')
    currency_id = fields.Many2one(related='company_id.currency_id', string=u'公司货币', store=True, index=True)
    supplier_amount_advance_payment = fields.Float('u预付总金额', compute=compute_supplier_amount_residual_advance_payment)
    supplier_amount_residual_advance_payment = fields.Float('预付余额', compute=compute_supplier_amount_residual_advance_payment)

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

    amount_invoice_org_new = fields.Monetary(u'发票金额',compute=compute_by_invoice_line_ids,store=True)#按照明细的发票进行汇总计算

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
    line_do_ids = fields.Many2many('account.reconcile.order.line', ) #compute=compute_line_do_ids,
    line_ids = fields.One2many('account.reconcile.order.line', 'order_id', u'明细')


    line_no_ids = fields.One2many('account.reconcile.order.line.no', 'order_id',u'明细')
    line_no_other_ids = fields.Many2many('account.reconcile.order.line.no','ref_line_no', 'lid', 'rid',  u'明细')

    # line_no_compute_ids = fields.One2many('account.reconcile.order.line.no', compute=compute_line_no_compute_ids, string='本次认领账单')
    move_ids = fields.One2many('account.move', 'reconcile_order_id', u'分录')

    yjzy_payment_id = fields.Many2one('account.payment', u'选择收款单')
    fkzl_id = fields.Many2one('account.payment', u'付款指令')
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'认领余额', related = 'yjzy_payment_id.balance',  currency_field='yjzy_payment_currency_id',)
    # compute=compute_yjzy_payment_balance,

    be_renling = fields.Boolean(u'是否认领单')
    sfk_type = fields.Selection(sfk_type, u'收付类型')

    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    other_payment_bank_id = fields.Many2one('res.partner.bank', u'其他支付银行账号')
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

    def update_move_line_new_advance_payment_id(self):
        for one in self.line_ids.filtered(lambda x: x.amount_advance_org != 0):
            for line in self.move_ids:
                for x in line.line_ids:
                    # if (x.amount_currency == one.amount_advance_org or x.amount_currency == -one.amount_advance_org) and \
                    #         x.new_advance_payment_id != one.yjzy_payment_id:
                    if (x.account_id.code in ['2203','1123'] and (x.amount_currency == one.amount_advance_org or x.amount_currency == -one.amount_advance_org))  and one.yjzy_payment_id and x.new_advance_payment_id != one.yjzy_payment_id:
                        x.new_advance_payment_id = one.yjzy_payment_id

    def open_rcskd(self):
        form_view = self.env.ref('yjzy_extend.view_rcskd_form_new')
        return {
            'name': '查看日常收款单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.payment',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.yjzy_payment_id.id,
            'target': 'new',
            'context': {'show_shoukuan': True,
                         'default_sfk_type': 'rcskd',
                         'default_payment_type': 'inbound',
                         'default_be_renling': False,
                         'default_advance_ok': True,
                         'default_partner_type': 'customer'}
        }

    def action_to_fkzl(self):
        stage_id = self._stage_find(domain=[('code', '=', '055')])
        print('action_to_fkzl',stage_id)
        self.write({'stage_id': stage_id.id,
                    })

    def action_delete_fkzl(self):
        stage_id = self._stage_find(domain=[('code', '=', '050')])
        print('action_to_fkzl',stage_id)
        self.write({'stage_id': stage_id.id,
                    })
    #1215
    def make_account_payment_state_ids(self):
        account_payment_state_ids = self.supplier_advance_payment_ids
        account_payment_state_obj = self.env['account.payment.state']
        for one in account_payment_state_ids:
            account_payment_state_id = account_payment_state_obj.create({
                'advance_payment_id':one.id,
                'reconcile_order_id':self.id,
                'amount_advance_balance_d':one.advance_balance_total,
            })

    #从预付款单创建申请
    def make_account_payment_state_ids_from_advance(self,advance_payment_id):
        account_payment_state_obj = self.env['account.payment.state']
        account_payment_state_id = account_payment_state_obj.create({
            'advance_payment_id':advance_payment_id.id,
            'reconcile_order_id':self.id,
            'amount_advance_balance_d':advance_payment_id.advance_balance_total,
            'state':'reconcile',
        })
        account_payment_state_id.action_add_yjzy_payment_id()


    def name_get(self):
        res = []
        ctx = self.env.context
        for one in self:
            if ctx.get('default_sfk_type', '') == 'yfhxd' and one.hxd_type_new == '30':
                name = '%s:%s' % ('预付-应付认领', one.name)
            elif ctx.get('default_sfk_type', '') == 'yfhxd' and one.hxd_type_new == '40' and one.operation_wizard != '03':
                if one.invoice_attribute == 'other_payment':
                    name = '%s:%s' % ('其他应付付款申请', one.name)
                else:
                    name = '%s:%s' % ('应付付款申请', one.name)
            elif ctx.get('default_sfk_type', '') == 'yfhxd' and one.hxd_type_new == '40' and one.operation_wizard == '03':
                name = '%s:%s' % ('应付申请前的预付认领审批', one.name)

            else:
                name = one.name
            res.append((one.id, name))
        return res

    # def open_yjzy_reconcile_order_id(self):
    #     form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new_for_advance_approve')
    #     if not self.yjzy_reconcile_order_approval_ids:
    #         self.action_manager_approve_first_stage()
    #     else:
    #         return {
    #             'name': '预付-应付认领列表',
    #             'view_type': 'form',
    #             "view_mode": 'form',
    #             'res_model': 'account.reconcile.order',
    #             'type': 'ir.actions.act_window',
    #             'views': [(form_view.id, 'form')],
    #             'res_id': self.id,
    #             'target': 'new',
    #             'context': {'fk_journal_id': 1,
    #                         'show_so': 1,                        }
    #         }

    @api.onchange('other_payment_bank_id')
    def onchange_other_payment_bank_id(self):
        if self.invoice_attribute == 'other_payment':
           self.bank_id = self.other_payment_bank_id

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
            'view_type': 'form',
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
        for one in self.invoice_ids:
            one.write({'state_2':'30_no_account_payment'})
        return res


    # def action_05(self):
    #     self.operation_wizard = '05'
    #     self.make_lines()


    @api.onchange('yjzy_advance_payment_id')
    def onchange_yjzy_advance_payment_id(self):
        if self.reconcile_payment_ids:
            raise Warning('已经生成认领单，不可修改预付单')
        for one in self.line_no_ids:
            one.yjzy_payment_id = self.yjzy_advance_payment_id
        # for one in self.line_ids:
        #     one.yjzy_payment_id = self.yjzy_advance_payment_id

    #分别创建需要的付款单（原生）  #ok_1218
    def create_yjzy_payment_ysrl(self):
        self.ensure_one()
        self.reconcile_payment_ids.unlink()
        sfk_type = 'yingshourld'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        account_payment_obj = self.env['account.payment']
        partner_id = self.partner_id
        yjzy_payment_id = self.yjzy_payment_id
        line_ids = self.line_ids

        line_no_ids = self.line_no_ids
        journal_domain_yszk = [('code', '=', 'yszk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yszk = self.env['account.journal'].search(journal_domain_yszk, limit=1)
        journal_domain_ysdrl = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_ysdrl = self.env['account.journal'].search(journal_domain_ysdrl, limit=1)
        journal_domain_yhkk = [('code', '=', 'yhkk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yhkk = self.env['account.journal'].search(journal_domain_yhkk, limit=1)
        journal_domain_xsfy = [('code', '=', 'xsfy'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_xsfy = self.env['account.journal'].search(journal_domain_xsfy, limit=1)

        for line_no in line_no_ids:
            if line_no.amount_payment_org > 0:
                reconcile_payment_no_id = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
                    'account_reconcile_order_line_no_id': line_no.id,
                    'name': name,
                    'sfk_type': sfk_type,
                    'partner_id': partner_id.id,
                    'yjzy_payment_id': yjzy_payment_id.id,
                    'amount': line_no.amount_payment_org,
                    'currency_id': line_no.payment_currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_ysdrl.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line_no.invoice_id.id, None)],
                    # 'po_id': line_no.po_id.id,
                    'invoice_log_id': line_no.invoice_id.id,
                    'reconcile_type': '30_payment_in',
                    'post_date': fields.date.today()
                })

        for line in line_ids:
            if line.amount_payment_org > 0:
                reconcile_payment_id = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
                    'account_reconcile_order_line_id': line.id,
                    'name': name,
                    'partner_id': partner_id.id,
                    'yjzy_payment_id': yjzy_payment_id.id,
                    'amount': line.amount_payment_org,
                    'currency_id': line.payment_currency_id.id,
                    'sfk_type': sfk_type,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_ysdrl.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],  # 参考m2m
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '30_payment_in',
                    'post_date': fields.date.today(),
                    'so_id':line.so_id.id,
                    # 'invoice_log_id': line.invoice_id.id,
                })
            if line.amount_advance_org > 0:
                print('journal_id_yszk',journal_id_yszk)
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id': partner_id.id,
                    'amount': line.amount_advance_org,
                    'sfk_type': sfk_type,
                    'currency_id': line.yjzy_currency_id.id,
                    'yjzy_payment_id':line.yjzy_payment_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_yszk.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'so_id': line.so_id.id,
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '40_advance_in',
                })
            if line.amount_bank_org > 0:
                reconcile_payment_id_3 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
                    'account_reconcile_order_line_id': line.id,
                    'name':name,
                    'partner_id': partner_id.id,
                    'amount': line.amount_bank_org,
                    'sfk_type': sfk_type,
                    'currency_id': line.invoice_currency_id.id,
                    'payment_type': 'inbound',
                    'partner_type': 'customer',
                    'advance_ok': False,
                    'journal_id': journal_id_yhkk.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line.invoice_id.id, None)],
                    'so_id': line.so_id.id,
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '50_reconcile',
                })

            if line.amount_diff_org > 0:
                reconcile_payment_id_4 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
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
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '50_reconcile',
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
        line_no_ids = self.line_no_ids
        journal_domain_yfzk = [('code', '=', 'yfzk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yfzk = self.env['account.journal'].search(journal_domain_yfzk, limit=1)
        journal_domain_yfdrl = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yfdrl = self.env['account.journal'].search(journal_domain_yfdrl, limit=1)
        journal_domain_yhkk = [('code', '=', 'yhkk'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_yhkk = self.env['account.journal'].search(journal_domain_yhkk, limit=1)
        journal_domain_xsfy = [('code', '=', 'xsfy'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_xsfy = self.env['account.journal'].search(journal_domain_xsfy, limit=1)
        for line_no in line_no_ids:
            if line_no.amount_payment_org > 0:
                reconcile_payment_no_id = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
                    'account_reconcile_order_line_no_id': line_no.id,
                    'name': name,
                    'sfk_type': sfk_type,
                    'partner_id': partner_id.id,
                    'yjzy_payment_id': yjzy_payment_id.id,
                    'amount': line_no.amount_payment_org,
                    'currency_id': line_no.payment_currency_id.id,
                    'payment_type': 'outbound',
                    'partner_type': 'supplier',
                    'advance_ok': False,
                    'journal_id': journal_id_yfdrl.id,
                    'payment_method_id': 2,
                    'invoice_ids': [(4, line_no.invoice_id.id, None)],
                    # 'po_id': line_no.po_id.id,
                    'invoice_log_id':line_no.invoice_id.id,
                    'reconcile_type':'10_payment_out',
                    'post_date':fields.date.today()
                })

        for line in line_ids:
            if line.amount_payment_org > 0:
                reconcile_payment_id = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
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
                    'invoice_log_id':line.invoice_id.id,
                    'reconcile_type': '10_payment_out',
                    'post_date': fields.date.today()
                })
            if line.amount_advance_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
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
                    'yjzy_payment_id':line.yjzy_payment_id.id,
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '20_advance_out',
                    'post_date': fields.date.today()
                })
            if line.amount_bank_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
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
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '60_reconcile',
                    'post_date': fields.date.today()
                })

            if line.amount_diff_org > 0:
                reconcile_payment_id_2 = account_payment_obj.create({
                    'account_reconcile_order_id': self.id,
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
                    'invoice_log_id': line.invoice_id.id,
                    'reconcile_type': '60_reconcile',
                    'post_date': fields.date.today()
                })
    #判断预付金额和预付款单的余额问题
    # @api.onchange('line_no_ids')
    # def _onchange_line_no_ids(self):
    #     if self.operation_wizard in ['10','40','30']:
    #
    #         self.update_line_amount()
    #     if self.operation_wizard in ['25']:
    #
    #         self.update_line_advance_amount() #预收预付 将不会使用自动分配
    #同时认领的时候，从明细反馈数据到非明细
    # @api.onchange('line_ids')
    # def _onchange_line_ids(self):
    #     #
    #     if self.hxd_type_new in ['25']:
    #         self.update_line_advance_no_amount()

    def update_yjzy_payment_yfrl(self):
        self.ensure_one()
        yjzy_payment_id = self.yjzy_payment_id

        line_ids = self.line_ids
        line_no_ids = self.line_no_ids
        for line_no in line_no_ids:
            for rld_1 in line_no.yingshouyingfurld_ids:
                rld_1.write({
                    'yjzy_payment_id': yjzy_payment_id.id,
                    'post_date': fields.date.today()
                })
        for line in line_ids:
            for rld_2 in line.yingshouyingfurld_ids:
                rld_2.write({
                    'post_date': fields.date.today()
                })

    def update_line_advance_no_amount(self):
        for one in self.line_no_ids:
            line_ids = self.line_ids.filtered(lambda x: x.invoice_id == one.invoice_id)
            amount_invoice = sum(x.amount_advance_org for x in line_ids)
            one.amount_advance_org = amount_invoice



    def open_wizard_reconcile_invoice(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        invoice_obj = self.env['account.invoice.line']
        if self.sfk_type == 'yshxd':
            so_id = self.so_id
            if so_id:
                invoice_lines = invoice_obj.search([('so_id', '=', so_id.id),('invoice_yjzy_type_1','=','sale')])
                print('invoice_lines_akiny', invoice_lines)
                invoice_ids = invoice_lines.mapped('invoice_id')
                form_view = self.env.ref('yjzy_extend.wizard_reconcile_invoice_form').id
            else:
                invoice_ids = None
                form_view = self.env.ref('yjzy_extend.wizard_reconcile_invoice_no_po_form').id
            print('invoice_ids_akiny', invoice_ids.ids)
            ctx.update({
                'default_partner_id': self.partner_id.id,
                'default_order_id':self.id,
                'default_invoice_ids':self.invoice_ids.ids,
                'sfk_type':self.sfk_type,
                'default_yjzy_advance_payment_id':self.yjzy_advance_payment_id.id,
                'default_yjzy_type':self.yjzy_type,
                'default_yjzy_advance_payment_id_sfk_type': self.sfk_type
            })
            return {
                'name': '添加账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.reconcile.invoice',
                # 'res_id': bill.id,
                'views': [(form_view, 'form')],
                'target': 'new',
                'type': 'ir.actions.act_window',
                'context': ctx,
            }
        if self.sfk_type == 'yfhxd':
            po_id = self.yjzy_advance_payment_id.po_id

            if po_id:
                invoice_lines = invoice_obj.search([('purchase_id', '=', po_id.id)])
                print('invoice_lines_akiny', invoice_lines)
                invoice_ids = invoice_lines.mapped('invoice_id')
                form_view = self.env.ref('yjzy_extend.wizard_reconcile_invoice_form').id
            else:
                invoice_ids = None
                form_view = self.env.ref('yjzy_extend.wizard_reconcile_invoice_no_po_form').id
            print('invoice_ids_akiny', invoice_ids.ids)


            ctx.update({
                'default_partner_id': self.partner_id.id,
                'default_order_id': self.id,
                'default_invoice_ids': self.invoice_ids.ids,
                'sfk_type': self.sfk_type,
                'default_yjzy_advance_payment_id': self.yjzy_advance_payment_id.id,
                'default_invoice_po_so_ids': invoice_ids.ids,
                'default_type': 'in_invoice',
                'default_yjzy_advance_payment_id_sfk_type': self.sfk_type
            })
            return {
                'name': '添加账单',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'wizard.reconcile.invoice',
                # 'res_id': bill.id,
                'views': [(form_view, 'form')],
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

    def action_unlink(self):
        self.unlink()
        return {'type': 'ir.actions.act_window_close'}

    def unlink(self):
        for one in self:
            if one.state not in ['cancelled','draft']:
                raise Warning(u'只有取消草稿状态允许删除')
        return super(account_reconcile_order, self).unlink()

    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['account.reconcile.stage'].search(search_domain, order=order, limit=1)

    #审批新

    #提交：
    #预付预收提交、应收应付提交、预收预付同时提交
    def action_submit_stage(self):
        self.ensure_one()
        if self.state_1 not in ['draft','draft_yshxd','draft_all','account_approval','account_approval_yshxd']:
            raise Warning('非可提交状态，不允许提交！')
        if self.sfk_type == 'yfhxd':
            hxd_type_new = self.hxd_type_new
            operation_wizard = self.operation_wizard
            lines = self.line_ids
            line_do_ids = self.line_do_ids
            if hxd_type_new == '40':
                if operation_wizard == '20':
                    if self.amount_total_org == 0:
                        raise Warning('认领金额为0，无法提交！')
                    for one in lines:
                        if one.po_id:
                            if one.amount_advance_org > one.amount_invoice_so_residual_can_approve:
                                raise Warning('预付认领金额大于可认领应付金额')
                            if one.advance_residual2 >=0 and one.amount_advance_org > one.advance_residual2:
                                raise Warning('预付认领金额大于可认领的预付金额')
                            if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                                raise Warning('预付认领金额大于可认领的预付金额')
                    # for one in line_do_ids:
                    #     if one.amount_advance_org == 0 and one.po_id:
                    #         raise Warning('有明细行预付金额为0，请填写或者删除明细行！')
                    stage_id = self._stage_find(domain=[('code', '=', '020')])
                    self.write({'stage_id': stage_id.id,
                                'state': 'posted',
                                # 'operation_wizard':'25'
                                })
                if operation_wizard == '03':
                    for one in lines:
                        if one.po_id:
                            if one.amount_advance_org > one.amount_invoice_so_residual_can_approve:
                                raise Warning('预付认领金额大于可认领应付金额')
                            if one.advance_residual2 >=0 and one.amount_advance_org > one.advance_residual2:
                                raise Warning('预付认领金额大于可认领的预付金额')
                            if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                                raise Warning('预付认领金额大于可认领的预付金额')
                    for one in self.line_do_ids:
                        if one.amount_advance_org == 0 and one.po_id:
                            raise Warning('有明细行预付金额为0，请填写或者删除明细行！')
                    stage_id = self._stage_find(domain=[('code', '=', '020')])
                    self.write({'stage_id': stage_id.id,
                                'state': 'posted',
                                # 'operation_wizard':'25'
                                })
            if hxd_type_new == '30':
                for one in lines:
                    if one.po_id:
                        if one.amount_advance_org > one.amount_invoice_so_residual_can_approve:
                            raise Warning('预付认领金额大于可认领应付金额')
                        if one.advance_residual2 >= 0 and one.amount_advance_org > one.advance_residual2:
                            raise Warning('预付认领金额大于可认领的预付金额')
                        if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                            raise Warning('预付认领金额大于可认领的预付金额')
                for one in self.line_do_ids:
                    if one.amount_advance_org == 0 and one.po_id:
                        raise Warning('有明细行预付金额为0，请填写或者删除明细行！')
                stage_id = self._stage_find(domain=[('code', '=', '020')])
                self.write({'stage_id': stage_id.id,
                            'state': 'posted',
                            # 'operation_wizard':'25'
                            })

        if self.sfk_type == 'yshxd':
            hxd_type_new = self.hxd_type_new
            operation_wizard = self.operation_wizard
            lines = self.line_ids
            line_do_ids = self.line_do_ids
            if hxd_type_new == '10':
                if operation_wizard == '20':
                    if self.amount_total_org == 0:
                        raise Warning('认领金额为0，无法提交！')
                    for one in lines:
                        if one.so_id:
                            if one.amount_advance_org > one.amount_invoice_so_residual_can_approve:
                                raise Warning('预收认领金额大于可认领应收金额')
                            if one.advance_residual2 >= 0 and one.amount_advance_org > one.advance_residual2:
                                raise Warning('预收认领金额大于可认领应收金额')
                            if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                                raise Warning('预收认领金额大于可认领应收金额')
                    for one in line_do_ids:
                        if one.amount_advance_org == 0 and one.so_id:
                            raise Warning('有明细行预收金额为0，请填写或者删除明细行！')
                    stage_id = self._stage_find(domain=[('code', '=', '025')])
                    self.write({'stage_id': stage_id.id,
                                'state': 'posted',
                                })
                if operation_wizard == '03':
                    for one in lines:
                        if one.so_id:
                            if one.amount_advance_org > one.amount_invoice_so_residual_can_approve:
                                raise Warning('预收认领金额大于可认领应收金额')
                            if one.advance_residual2 >= 0 and one.amount_advance_org > one.advance_residual2:
                                raise Warning('预收认领金额大于可认领应收金额')
                            if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                                raise Warning('预收认领金额大于可认领应收金额')
                    for one in self.line_do_ids:
                        if one.amount_advance_org == 0 and one.so_id:
                            raise Warning('有明细行预付金额为0，请填写或者删除明细行！')
                    stage_id = self._stage_find(domain=[('code', '=', '025')])
                    self.write({'stage_id': stage_id.id,
                                'state': 'posted',

                                })
        return True
    #预付的审批
    def action_manager_approve_first_stage(self):
        # if self.state_1 not in ('advance_approval','advance_approval_yshxd'):
        #     raise Warning('非可审批状态，不允许审批！')
        if self.sfk_type == 'yfhxd':
            amount_payment_can_approve_all = sum(x.amount_payment_can_approve_all for x in self.invoice_ids)
            print('amount_payment_can_approve_all_akiny',amount_payment_can_approve_all)
            if not self.line_do_ids and self.operation_wizard == '03':#如果是前置预付，那么如果没有需要认领的预付，就直接转换为应付
                if amount_payment_can_approve_all == 0:
                    raise Warning('提交的账单的可申请金额为0，请检查等待认领的账单！')
                # self.operation_wizard = '10'
                stage_id = self._stage_find(domain=[('code', '=', '030')])
                self.write({'stage_id': stage_id.id,
                            'state': 'posted',
                            'operation_wizard': '10',
                            'hxd_type_new':'40',
                            })
                # self.make_lines()
                view = self.env.ref('sh_message.sh_message_wizard')
                view_id = view and view.id or False
                context = dict(self._context or {})
                context['message'] = "审批完成，等待财务继续提交付款申请"
                context['res_model'] = "account.reconcile.order"
                context['res_id'] = self.id
                context['views'] = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
                context['no_advance'] = True
                print('context_akiny', context)
                return {
                    'name': 'Success',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'sh.message.wizard',
                    'views': [(view_id, 'form')],
                    'target': 'new',
                    'context': context,
                }
            else:
                self.action_manager_approve_stage()
                if self.hxd_type_new == '30':
                    stage_id = self._stage_find(domain=[('code', '=', '060')])
                    self.write({'stage_id': stage_id.id,
                                'state': 'done',
                                # 'operation_wizard': '03',
                                })
                else:
                    self.operation_wizard = '20'
                    self.hxd_type_new = '30'
                    if amount_payment_can_approve_all == 0: # 当预付把这次认领的账单全部认领完了，这个应付申请单 就直接跳转完成
                        stage_id = self._stage_find(domain=[('code', '=', '060')])
                        self.write({'stage_id': stage_id.id,
                                    'state': 'done',
                                    # 'operation_wizard': '03',
                            })
                    else:
                        if self.yjzy_reconcile_order_id_new:
                            raise Warning('已经审批过一次')
                        invoice_dic = []
                        for one in self.invoice_ids:            #如果invoice是0 余额的 可以从invoice_ids中删除了
                            if one.amount_payment_can_approve_all != 0:
                                invoice_dic.append(one.id)
                        print('invoice_dic', invoice_dic)
                        sfk_type = 'yfhxd'
                        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
                        form_view = self.env.ref('yjzy_extend.account_yfhxd_form_view_new')
                        account_reconcile_order_obj = self.env['account.reconcile.order']
                        account_reconcile_id = account_reconcile_order_obj.create({
                            'partner_id': self.partner_id.id,
                            'manual_payment_currency_id': self.manual_payment_currency_id.id,
                            'invoice_ids': [(6, 0, invoice_dic)], #akiny参考
                            'payment_type': 'outbound',
                            'partner_type': 'supplier',
                            'sfk_type': 'yfhxd',
                            'be_renling': True,
                            'name': name,
                            'journal_id': self.journal_id.id,
                            'payment_account_id': self.payment_account_id.id,
                            # 'operation_wizard':operation_wizard,
                            'hxd_type_new':'40',
                            'operation_wizard':'10',
                            'purchase_code_balance': 1,
                            'invoice_attribute': self.invoice_attribute,
                            'invoice_partner': self.invoice_partner,
                            'name_title': self.name_title,
                            'yjzy_reconcile_order_id_new':self.id
                        })
                        stage_id = self._stage_find(domain=[('code', '=', '030')])
                        account_reconcile_id.write({'stage_id': stage_id.id,
                                                    'state': 'posted',
                                                    'operation_wizard': '10',
                                                    })
                        account_reconcile_id.make_lines()
                        self.yjzy_reconcile_order_id_new = account_reconcile_id
                        view=self.env.ref('sh_message.sh_message_wizard')
                        view_id = view and view.id or False
                        context = dict(self._context or {})
                        context['message'] = "审批完成"
                        context['res_model'] = "account.reconcile.order"
                        context['res_id'] = account_reconcile_id.id
                        context['views'] = self.env.ref('yjzy_extend.account_yfhxd_form_view_new').id
                        # context['no_advance'] = False
                        print('context_akiny',context)
                        return{
                            'name':'Success',
                            'type':'ir.actions.act_window',
                            'view_type':'form',
                            'view_mode':'form',
                            'res_model':'sh.message.wizard',
                            'views':[(view_id,'form')],
                            'target':'new',
                            'context':context,
                        }



    # 财务审批：预付没有审批，只有应付申请的时候才会审批。
    def action_account_approve_stage(self):
        # if self.state_1 not in ['account_approval', 'account_approval_yshxd']:
        #     raise Warning('非可审批状态，不允许审批！')
        if self.amount_total_org == 0:
            raise Warning('认领金额为0，无法提交！')
        for one in self.line_no_ids:
            if one.amount_payment_can_approve_all < one.amount_payment_org:
                raise Warning('申请的金额大于可申请的应付,请检查')
        if self.sfk_type == 'yfhxd':
            if self.hxd_type_new == '40':
                if not self.bank_id:
                    raise Warning('请填写收款单账号')
                if not self.fk_journal_id:
                    raise Warning('请填写付款银行')
            stage_id = self._stage_find(domain=[('code', '=', '040')])
            self.write({'stage_id': stage_id.id,
                        'state': 'posted',
                        })
        if self.sfk_type == 'yshxd':
            self.action_manager_approve_stage()

    # 总经理审批：如果是预付申请，直接完成makedone，只有应付申请的时候才会审批。
    def action_manager_approve_stage(self):
        self.ensure_one()

        if self.sfk_type == 'yfhxd':

            if self.operation_wizard in ['10', '30']:
                # if self.state_1 not in ['manager_approval', 'manager_approval_yshxd', 'manager_approval_all']:
                #     raise Warning('非可审批状态，不允许审批！')
                self.create_rcfkd()
                stage_id = self._stage_find(domain=[('code', '=', '050')])
                self.write({'stage_id': stage_id.id,
                            'state': 'approved',
                            'approve_date': fields.date.today(),
                            'approve_uid': self.env.user.id
                            })
            self.create_yjzy_payment_yfrl()  #生成应付认领单
            if self.operation_wizard in ['03','20', '25']:
                # if self.state_1 not in ['manager_approval','advance_approval','advance_approval_yshxd', 'manager_approval_yshxd', 'manager_approval_all']:
                #     raise Warning('非可审批状态，不允许审批！')
                self.action_done_new_stage()
                # self.action_done_new() #生成的应付认领单过账
                self.write({'approve_date': fields.date.today(),
                            'approve_uid': self.env.user.id
                            })

        if self.sfk_type == 'yshxd':
            # if self.state_1 not in ['draft','manager_approval', 'manager_approval_yshxd','draft_yshxd','account_approval_yshxd', 'manager_approval_all']:
            #     raise Warning('非可审批状态，不允许审批！')
            print('sfk_type_____111',self.sfk_type)
            if not self.yjzy_payment_id and self.hxd_type_new in ['20','25']:
                raise Warning('没有对应的收款单，请检查！')
            if not self.yjzy_advance_payment_id and self.hxd_type_new == '10':
                raise Warning('没有对应的预收认领单，请检查！')
            self.create_yjzy_payment_ysrl()
            self.action_done_new()#生成的yingshourld过账并核销
            if self.back_tax_declaration_id and self.back_tax_declaration_id.declaration_amount_all_residual_new == 0:
                self.back_tax_declaration_id.state = 'paid'
            stage_id = self._stage_find(domain=[('code', '=', '060')])
            self.write({'stage_id': stage_id.id,
                        'state': 'done',
                        'approve_date': fields.date.today(),
                        'approve_uid': self.env.user.id
                        })
            #收付款单的核销的动作这里完成，
            if self.yjzy_payment_id:
                self.yjzy_payment_id.action_reconcile()
            if self.yjzy_advance_payment_id:
                self.yjzy_advance_payment_id.action_reconcile()

        return True




    #预收确认认领
    def action_confirm_ysrld_stage(self):
        self.ensure_one()
        if self.hxd_type_new in ['10','25'] and self.amount_total_org == 0:
            raise Warning('认领金额为0，无法提交！')
        if self.hxd_type_new == '25' and (self.yjzy_payment_balance != 0 and self.amount_payment_org_new == 0):
            raise Warning('收款认领金额为0，无法提交！')
        if self.hxd_type_new == '20' and self.amount_payment_org == 0:
            raise Warning('认领金额为0，无法提交！')
        if self.amount_payment_org_new > self.yjzy_payment_balance:
            raise Warning('认领金额大于可认领的收款金额，无法提交！')
        lines = self.line_ids
        if lines:
            for one in lines:
                if one.so_id:
                    if one.amount_total_org_new > one.amount_invoice_so_residual_can_approve:
                        raise Warning('申请的金额大于可认领预收')
                    if one.amount_advance_org > one.yjzy_payment_id.advance_balance_total:
                        raise Warning('预收认领金额大于可认领的预收金额')
        if self.line_do_ids and self.amount_advance_org == 0:
            raise Warning('预收认领金额为0，无法提交！')
        for one in self.line_no_ids:
            if one.amount_payment_can_approve_all < one.amount_payment_org:
                raise Warning('收款的认领金额大于可认领的应收,请检查')
        self.action_manager_approve_stage()#完成当前的应收的审批过账
        invoice_dic = []
        for one in self.invoice_ids:  # 如果invoice是0 余额的 可以从invoice_ids中删除了
            if one.amount_payment_can_approve_all != 0:
                invoice_dic.append(one.id)
        print('invoice_dic', invoice_dic)
        # if self.hxd_type_new == '20' and invoice_dic != False and self.account_payment_state_ids != False:
        #     #如果同时认领 后面的就不需要创建了
        #     sfk_type = 'yshxd'
        #     name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        #     form_view = self.env.ref('yjzy_extend.account_yshxd_form_view_new')
        #     account_reconcile_order_obj = self.env['account.reconcile.order']
        #     account_reconcile_id = account_reconcile_order_obj.create({
        #         'partner_id': self.partner_id.id,
        #         'manual_payment_currency_id': self.manual_payment_currency_id.id,
        #         'invoice_ids': [(6, 0, invoice_dic)],  # akiny参考
        #         'payment_type': 'inbound',
        #         'partner_type': 'customer',
        #         'sfk_type': 'yshxd',
        #         'be_renling': True,
        #         'name': name,
        #         'journal_id': self.journal_id.id,
        #         'payment_account_id': self.payment_account_id.id,
        #         # 'operation_wizard':operation_wizard,
        #         'hxd_type_new': '10',
        #         'operation_wizard': '20',
        #         'purchase_code_balance': 1,
        #         'invoice_attribute': self.invoice_attribute,
        #         'invoice_partner': self.invoice_partner,
        #         'name_title': self.name_title,
        #         'yjzy_reconcile_order_id_new': self.id
        #     })
        #     account_reconcile_id.make_lines()
        #     account_reconcile_id.make_account_payment_state_ids()
        #     self.yjzy_reconcile_order_id_new = account_reconcile_id
        #     view = self.env.ref('sh_message.sh_message_wizard')
        #     view_id = view and view.id or False
        #     context = dict(self._context or {})
        #     context['message'] = "审批完成"
        #     context['res_model'] = "account.reconcile.order"
        #     context['res_id'] = account_reconcile_id.id
        #     context['views'] = self.env.ref('yjzy_extend.account_yshxd_form_view_new').id
        #     # context['no_advance'] = False
        #     print('context_akiny', context)
        #     return {
        #         'name': 'Success',
        #         'type': 'ir.actions.act_window',
        #         'view_type': 'form',
        #         'view_mode': 'form',
        #         'res_model': 'sh.message.wizard',
        #         'views': [(view_id, 'form')],
        #         'target': 'new',
        #         'context': context,
        #     }

        # self.make_account_payment_state_ids()

    def action_done_new_stage(self):
        stage_id = self._stage_find(domain=[('code', '=', '060')])
        print('state_id_akiny',stage_id.code)
        self.write({'stage_id': stage_id.id,
                    'state': 'done',
                    })
        self.action_done_new()#对应的生成预付待认领的那个付款单的过账
        #1203取消
        # if self.line_ids:
        #     for x in self.line_ids:
        #         x.amount_invoice_so_residual_d_after = x.amount_invoice_so_residual_d - x.amount_total_org_new
        #         x.amount_invoice_so_residual_can_approve_d_after = x.amount_invoice_so_residual_can_approve_d - x.amount_total_org_new
        # if self.line_no_ids:
        #     for line in self.line_no_ids:
        #         line.amount_payment_can_approve_all_after = line.amount_payment_can_approve_all_this_time - line.amount_total_org_new
        #         line.invoice_residual_after = line.invoice_residual_after - line.amount_total_org_new

        # if self.account_payment_state_ids:
        #     for x in self.account_payment_state_ids:
        #         if x.reconcile_order_line_id:
        #             x.amount_advance_balance_after = x.amount_advance_balance_d - x.reconcile_order_line_id.amount_total_org_new
        #             x.amount_reconcile = x.reconcile_order_line_id.amount_total_org_new

    def action_draft_stage(self):
        if self.sfk_type == 'yfhxd':
            self.yjzy_payment_id.unlink()
            if self.hxd_type_new == '30':
                stage_id = self._stage_find(domain=[('code', '=', '010')])
                self.write({'stage_id': stage_id.id,
                            'state': 'draft',
                            'approve_date': False,
                            'approve_uid': False
                            })
            else:
                if self.hxd_type_new == '40': #如果是应付，看是否前置，前置，退回草稿，否则退回财务申请
                    if self.operation_wizard == '03':
                        stage_id = self._stage_find(domain=[('code', '=', '010')])
                        self.write({'stage_id': stage_id.id,
                                    'state': 'draft',
                                    'approve_date': False,
                                    'approve_uid': False
                                    })
                    else:
                        stage_id = self._stage_find(domain=[('code', '=', '030')])
                        self.write({'stage_id': stage_id.id,
                                    'state': 'posted',
                                    'approve_date': False,
                                    'approve_uid': False
                                    })
        if self.sfk_type == 'yshxd':
            if self.hxd_type_new == '30':
                stage_id = self._stage_find(domain=[('code', '=', '010')])
                self.write({'stage_id': stage_id.id,
                            'state': 'draft',
                            'approve_date': False,
                            'approve_uid': False
                            })
            else:
                stage_id = self._stage_find(domain=[('code', '=', '030')])
                self.write({'stage_id': stage_id.id,
                            'state': 'posted',
                            'approve_date': False,
                            'approve_uid': False
                            })

#1126
    # def action_draft_stage_old(self):
    #     if self.sfk_type == 'yfhxd':
    #         self.yjzy_payment_id.unlink()
    #     for one in self.yjzy_reconcile_order_ids:
    #         if one.state == 'refused':
    #             one.action_draft_stage()
    #     stage_id = self._stage_find(domain=[('code', '=', '010')])
    #     self.write({'stage_id': stage_id.id,
    #                 'state': 'draft',
    #                 'approve_date': False,
    #                 'approve_uid': False
    #                 })

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

    #1126
    def action_refuse_stage_old(self,reason):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if user not in stage_preview.user_ids:
            raise Warning('您没有权限拒绝')
        else:
            if self.yjzy_reconcile_order_approval_ids:
                for one in self.yjzy_reconcile_order_approval_ids:
                    one.action_refuse_no_message()

            self.write({'stage_id': stage_id.id,
                        'state': 'refused',
                         })
            for tb in self:
                tb.message_post_with_view('yjzy_extend.reconcile_hxd_template_refuse_reason',
                                          values={'reason': reason, 'name': self.name},
                                          subtype_id=self.env.ref(
                                              'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式
    def action_refuse_no_message_old(self):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        self.write({'stage_id': stage_id.id,
                'state': 'refused',
                })


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
                for one in self.reconcile_payment_ids:#所有认领单  日志
                    one.state_1 = '60_done'
                    one.invoice_log_id.get_reconcile_order_line()
                    one.invoice_log_id_this_time = one.invoice_log_id.residual
        if self.sfk_type == 'yshxd':
            if self.reconcile_payment_ids:
                self.reconcile_payment_ids.post()
                for one in self.reconcile_payment_ids:#所有认领单
                    one.state_1 = '60_done'
                    one.invoice_log_id.get_reconcile_order_line()
                    one.invoice_log_id_this_time = one.invoice_log_id.residual



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

        invoice_attribute = self.invoice_attribute
        yjzy_type = self.yjzy_type
        if invoice_attribute == 'normal':
            rckfd_attribute = 'yfzk'
        elif yjzy_type == 'other_payment_purchase':
            rckfd_attribute = 'other_payment'
        elif invoice_attribute == 'other_po':
            rckfd_attribute = 'other_po'
        elif invoice_attribute == 'expense_po':
            rckfd_attribute = 'expense_po'
        else:
            rckfd_attribute = False




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
            'expense_sheet_id':self.expense_sheet_id.id,
            'rckfd_attribute':rckfd_attribute
        })
        if self.expense_sheet_id:
            self.expense_sheet_id.payment_id = payment.id #1009
        if payment.sfk_type == 'rcfkd':
            payment.state_fkzl = '05_fksq'
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

#1220
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
        line_ids = None
        self.line_ids = line_ids
        for invoice in self.invoice_ids:

            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                # if self.yjzy_advance_payment_id and not self.yjzy_advance_payment_id.po_id:#对是否有选定预付款单进行判断
                #     yjzy_payment_id = self.yjzy_advance_payment_id.id
                # else:
                #     yjzy_payment_id = False
                line = line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                    # 'yjzy_payment_id':yjzy_payment_id
                })
                # if yjzy_payment_id:
                #     self.write({'line_do_ids': [(4, line.id)]})
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for po, invlines in po_invlines.items():
                    if self.yjzy_advance_payment_id.po_id:
                        if po.id == self.yjzy_advance_payment_id.po_id.id:
                            yjzy_payment_id = self.yjzy_advance_payment_id.id
                        else:
                            yjzy_payment_id = False
                    else:
                        yjzy_payment_id = self.yjzy_advance_payment_id.id

                    line = line_obj.create({
                        'order_id': self.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'yjzy_payment_id': yjzy_payment_id,
                    })
                    print('yjzy_payment_id_akiny',yjzy_payment_id)
                    # if yjzy_payment_id:
                    #     self.write({'line_do_ids': [(4, line.id)]})
                    line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                    line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
        if not self.line_no_ids:
            self.make_line_no()


        #1220
    def make_line_no(self):
        if self.env.context.get('ysrld_amount') and self.env.context.get('ysrld_amount') > 0:#收款-预收认领的时候进行的判断
            amount = self.env.context.get('ysrld_amount')
        else:
            amount = 0
        print('amount_akiny',amount)
        self.ensure_one()
        line_no_obj = self.env['account.reconcile.order.line.no']
        self.line_no_ids = None
        advance_residual2 = 0
        advance_residual = 0
        for one in self.invoice_ids:
            if amount > 0:
                amount_payment_org = amount
            else:
                if one.invoice_attribute == 'expense_po':
                    amount_payment_org = one.amount_payment_can_approve_all
                elif one.invoice_attribute == 'other_payment':
                    amount_payment_org = one.amount_payment_can_approve_all
                else:
                    amount_payment_org = one.declaration_amount
            if one.type == 'out_invoice':
                so_ids = one.invoice_line_ids.mapped('so_id')
                advance_residual2 = sum(x.balance for x in so_ids)
            if one.type == 'in_invoice':
                po_ids = one.invoice_line_ids.mapped('purchase_id')
                advance_residual = sum(x.balance for x in po_ids)
            print('amount_payment_org_akiny',amount_payment_org)
            line_no = line_no_obj.create({
                'order_id': self.id,
                'invoice_id': one.id,
                'advance_residual':advance_residual,
                'advance_residual2': advance_residual2,
                'amount_payment_org': amount_payment_org
            })
            line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
            line_no.invoice_residual_this_time = line_no.invoice_residual
            self.write({'line_no_other_ids': [(4, line_no.id)]})




    #ok_1218
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
                line = line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                    'amount_payment_org': invoice.declaration_amount
                })
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for so, invlines in so_invlines.items():
                    if self.yjzy_advance_payment_id.so_id:
                        if so.id == self.yjzy_advance_payment_id.so_id.id:
                            yjzy_payment_id = self.yjzy_advance_payment_id.id
                        else:
                            yjzy_payment_id = False
                    else:
                        yjzy_payment_id = self.yjzy_advance_payment_id.id
                    line = line_obj.create({
                        'order_id': self.id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'yjzy_payment_id': yjzy_payment_id
                    })
                    line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                    line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
        if not self.line_no_ids:
            self.make_line_no()
        # so_po_dic = {}
        # print('line_obj', line_ids)
        # self.line_no_ids = None
        # yjzy_advance_payment_id = self.yjzy_advance_payment_id
        # for i in self.line_ids:
        #     invoice = i.invoice_id
        #     amount_invoice_so = i.amount_invoice_so
        #     advance_residual2 = i.advance_residual2
        #     amount_payment_org = i.amount_payment_org
        #     order = i.order_id
        #     yjzy_payment_id = i.yjzy_payment_id
        #     print('yjzy_payment_id_1111111', yjzy_payment_id)
        #
        #     k = invoice.id
        #     if k in so_po_dic:
        #         print('k',k)
        #         so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
        #         so_po_dic[k]['advance_residual2'] += advance_residual2
        #         so_po_dic[k]['amount_payment_org'] += amount_payment_org
        #         if not so_po_dic[k]['yjzy_payment_id']:
        #             so_po_dic[k]['yjzy_payment_id'] = yjzy_payment_id.id
        #     else:
        #         print('k1', k)
        #         so_po_dic[k] = {
        #                         'invoice_id':invoice.id,
        #                         'yjzy_payment_id': yjzy_payment_id.id,
        #                         'amount_invoice_so': amount_invoice_so,
        #                         'advance_residual2': advance_residual2,
        #                         'amount_payment_org':amount_payment_org}
        # for kk, data in list(so_po_dic.items()):
        #     line_no = line_no_obj.create({
        #         'order_id': self.id,
        #         'invoice_id': data['invoice_id'],
        #         'amount_invoice_so': data['amount_invoice_so'],
        #         'advance_residual2': data['advance_residual2'],
        #         'yjzy_payment_id': data['yjzy_payment_id'],
        #         'amount_payment_org':data['amount_payment_org'],
        #     })
        #     line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
        #     line_no.invoice_residual_this_time = line_no.invoice_residual



    #ok_1218  后期需要把它和make_line合并
    def _make_lines_po_from_expense(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        line_ids = None
        self.line_ids = line_ids
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
                    line = line_obj.create({
                        'order_id': self.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'amount_payment_org': sum([i.price_subtotal for i in invlines]),
                    })
                    line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                    line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
        # 826
        so_po_dic = {}
        print('line_obj', line_ids)
        self.line_no_ids = None
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
                # 'yjzy_payment_id': yjzy_advance_payment_id.id,

            })
            line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
            line_no.invoice_residual_this_time = line_no.invoice_residual

    # def _make_lines_po_from_expense(self):
    #     self.ensure_one()
    #     line_obj = self.env['account.reconcile.order.line']
    #     line_no_obj = self.env['account.reconcile.order.line.no']
    #     line_ids = None
    #     self.line_ids = line_ids
    #     for invoice in self.invoice_ids:
    #         po_invlines = self._prepare_purchase_invoice_line(invoice)
    #         if not po_invlines:
    #             line_obj.create({
    #                 'order_id': self.id,
    #                 'invoice_id': invoice.id,
    #                 'amount_invoice_so': invoice.amount_total,
    #                 'amount_payment_org': invoice.amount_total,
    #             })
    #         else:
    #             for po, invlines in po_invlines.items():
    #                 line = line_obj.create({
    #                     'order_id': self.id,
    #                     'po_id': po.id,
    #                     'invoice_id': invoice.id,
    #                     'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
    #                     'amount_payment_org': sum([i.price_subtotal for i in invlines]),
    #                 })
    #                 line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
    #                 line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
    #     # 826
    #     so_po_dic = {}
    #     print('line_obj', line_ids)
    #     self.line_no_ids = None
    #     for i in self.line_ids:
    #         invoice = i.invoice_id
    #         amount_invoice_so = i.amount_invoice_so
    #         advance_residual = i.advance_residual
    #         order = i.order_id
    #         k = invoice.id
    #         if k in so_po_dic:
    #             print('k', k)
    #             so_po_dic[k]['amount_invoice_so'] += amount_invoice_so
    #             so_po_dic[k]['advance_residual'] += advance_residual
    #         else:
    #             print('k1', k)
    #             so_po_dic[k] = {
    #                 'invoice_id': invoice.id,
    #                 'amount_invoice_so': amount_invoice_so,
    #                 'advance_residual': advance_residual, }
    #     for kk, data in list(so_po_dic.items()):
    #         line_no = line_no_obj.create({
    #             'order_id': self.id,
    #             'invoice_id': data['invoice_id'],
    #             'amount_invoice_so': data['amount_invoice_so'],
    #             'amount_payment_org': data['amount_invoice_so'],
    #             'advance_residual': data['advance_residual'],
    #             # 'yjzy_payment_id': yjzy_advance_payment_id.id,
    #
    #         })
    #         line_no.amount_payment_can_approve_all_this_time = line_no.invoice_id.amount_payment_can_approve_all
    #         line_no.invoice_residual_this_time = line_no.invoice_residual

    #826 拆分发票填写的金额到明细上
    def update_line_amount(self):
        for x in self.line_no_ids:
            invoice = x.invoice_id
            amount_payment_org = x.amount_payment_org
            amount_bank_org = x.amount_bank_org
            amount_diff_org = x.amount_diff_org
            #最新
            line_ids = self.line_ids.filtered(lambda x: x.invoice_id == invoice)
            print('line_ids[0]',line_ids[0])
            line_ids[0].amount_payment_org = amount_payment_org
            line_ids[0].amount_bank_org = amount_bank_org
            line_ids[0].amount_diff_org = amount_diff_org
            #1218删除
            # for line in line_ids:
            #     amount_invoice_so_proportion = line.amount_invoice_so_proportion
            #     line.amount_payment_org = amount_invoice_so_proportion * amount_payment_org
            #     line.amount_bank_org = amount_invoice_so_proportion * amount_bank_org
            #     line.amount_diff_org = amount_invoice_so_proportion * amount_diff_org

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

    def _compute_advice_amount_advance_org(self):
        so_id = self.yjzy_advance_payment_id.so_id
        po_id = self.yjzy_advance_payment_id.po_id
        so_line_ids = self.line_ids.filtered(lambda x: x.so_id == so_id)
        po_line_ids = self.line_ids.filtered(lambda x: x.po_id == po_id)
        so_amount_all = sum(x.amount_invoice_so for x in so_line_ids) #计算这次认领的发票的对应的销售的出运总金额，为了计算各自和他的比例
        po_amount_all = sum(x.amount_invoice_so for x in po_line_ids)
        if self.line_ids and self.line_no_ids:
            for one in self.line_no_ids:
                if self.sfk_type == 'yshxd':
                    invoice_id = one.invoice_id
                    line_id = self.line_ids.filtered(lambda x: x.so_id == so_id and x.invoice_id == invoice_id)
                    amount_invoice_so = line_id.amount_invoice_so

                    least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total - so_id.no_sent_amount_new
                    if least_advice_amount_advance_org < 0:
                        least_advice_amount_advance_org = 0


                    # one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.advance_balance_total
                    one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.amount + \
                                                    one.order_id.duoyu_this_time_advice_advance_org * (amount_invoice_so / so_amount_all)
                    one.least_advice_amount_advance_org = least_advice_amount_advance_org

                    print('werewrewrer',one.yjzy_payment_id.advance_balance_total)
                elif self.sfk_type == 'yfhxd':

                    invoice_id = one.invoice_id
                    line_id = self.line_ids.filtered(lambda x: x.po_id == po_id and x.invoice_id == invoice_id)
                    amount_invoice_so = line_id.amount_invoice_so
                    least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total - po_id.no_deliver_amount_new
                    if least_advice_amount_advance_org < 0:
                        least_advice_amount_advance_org = 0
                    one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.amount + \
                                                    one.order_id.duoyu_this_time_advice_advance_org * (amount_invoice_so / po_amount_all)
                    one.least_advice_amount_advance_org = least_advice_amount_advance_org
                    # one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.advance_balance_total
                    print('werewrewrer______', one.yjzy_payment_id.advance_balance_total,one.advice_amount_advance_org)

    def compute_advice_amount_advance_org(self):
        so_id = self.yjzy_advance_payment_id.so_id
        po_id = self.yjzy_advance_payment_id.po_id
        so_line_ids = self.line_ids.filtered(lambda x: x.so_id == so_id)
        po_line_ids = self.line_ids.filtered(lambda x: x.po_id == po_id)
        so_amount_all = sum(x.amount_invoice_so for x in so_line_ids) #计算这次认领的发票的对应的销售的出运总金额，为了计算各自和他的比例
        po_amount_all = sum(x.amount_invoice_so for x in po_line_ids)
        if self.line_ids and self.line_no_ids:
            for one in self.line_no_ids:
                if self.sfk_type == 'yshxd':
                    invoice_id = one.invoice_id
                    line_id = self.line_ids.filtered(lambda x: x.so_id == so_id and x.invoice_id == invoice_id)
                    amount_invoice_so = line_id.amount_invoice_so

                    least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total - so_id.no_sent_amount_new
                    if least_advice_amount_advance_org < 0:
                        least_advice_amount_advance_org = 0


                    # one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.advance_balance_total
                    one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.amount + \
                                                    one.order_id.duoyu_this_time_advice_advance_org * (amount_invoice_so / so_amount_all)
                    one.least_advice_amount_advance_org = least_advice_amount_advance_org

                    print('werewrewrer',one.yjzy_payment_id.advance_balance_total)
                elif self.sfk_type == 'yfhxd':
                    invoice_id = one.invoice_id
                    line_id = self.line_ids.filtered(lambda x: x.po_id == po_id and x.invoice_id == invoice_id)
                    po_id = self.line_ids.mapped('po_id')
                    amount_invoice_so = line_id.amount_invoice_so
                    # amount_org_hxd = self.yjzy_advance_payment_id.po_id.amount_org_hxd
                    amount_org_hxd = po_id.amount_org_hxd
                    # amount_po = self.yjzy_advance_payment_id.po_id.amount_total
                    amount_po = po_id.amount_total
                    rest_amount_org_hxd = amount_po - amount_org_hxd
                    least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total - po_id.no_deliver_amount_new - rest_amount_org_hxd#缺一个所有发票的未收金额
                    if least_advice_amount_advance_org < 0:
                        least_advice_amount_advance_org = 0
                    one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.amount - \
                                                    line_id.amount_advance_org_self + line_id.duoyu_this_time_advice_advance_org \
                                                    * (amount_invoice_so / so_amount_all)



                    one.least_advice_amount_advance_org = least_advice_amount_advance_org
                    # one.advice_amount_advance_org = line_id.so_tb_percent * one.yjzy_payment_id.advance_balance_total
                    print('werewrewrer______', one.yjzy_payment_id.advance_balance_total,one.advice_amount_advance_org)



#11-26预付和付款申请同一个入口的新方法
    def make_lines_11_16(self):
        if self.partner_type == 'customer':
            self._make_lines_so_new()
        if self.partner_type == 'supplier':
            self._make_lines_po_new()
            # if self.operation_wizard != '03':
            #     if self.hxd_type_new == '40':
            #         self.operation_wizard = '10'
            #     elif self.hxd_type_new == '30':
            #         self.operation_wizard = '25'

    #只有符合条件的make_line
    def _make_lines_po_new(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        account_payment_state_obj = self.env['account.payment.state']
        # line_ids = None
        # self.line_ids = line_ids

        if self.yjzy_advance_payment_id:
            yjzy_advance_payment_id = self.yjzy_advance_payment_id
        else:
            advance_payment_id = self.env.context.get('advance_payment_id') #从核销单上的预付单进行直接创建

            yjzy_advance_payment_id = self.env['account.payment'].search([('id','=',advance_payment_id)])
        account_payment_state_id = self.env.context.get('account_payment_state_id')
        print('yjzy_advance_payment_id_akiny',yjzy_advance_payment_id)
        print('le_akiny', len(self.line_ids), self.line_ids)
        if len(self.line_ids) != 0 and yjzy_advance_payment_id and not yjzy_advance_payment_id.po_id:
            raise Warning('已经有存在其他的认领明细，不允许认领没有采购合同的预付单！')
        for invoice in self.invoice_ids:
            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                line = line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,

                })
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for po, invlines in po_invlines.items():
                    if yjzy_advance_payment_id.po_id:
                        if po.id == yjzy_advance_payment_id.po_id.id:
                            yjzy_payment_id = yjzy_advance_payment_id.id
                        else:
                            yjzy_payment_id =False
                    else:
                        yjzy_payment_id = yjzy_advance_payment_id.id
                    #如果前端加了限制，这个就可以不用了
                    lines_same_count = len(self.line_ids.filtered(lambda x: (x.yjzy_payment_id.id == yjzy_payment_id and x.invoice_id.id == invoice.id) or
                                                                            (x.yjzy_payment_id and not x.yjzy_payment_id.po_id)))
                    print('line_same_count_akiny',lines_same_count,invoice.id)



                    if yjzy_advance_payment_id.po_id:
                        if (po.id == yjzy_advance_payment_id.po_id.id and lines_same_count == 0):
                            line=line_obj.create({
                                'order_id': self.id,
                                'po_id': po.id,
                                'invoice_id': invoice.id,
                                'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                                'yjzy_payment_id':yjzy_payment_id,
                                'account_payment_state_id':account_payment_state_id
                            })
                            line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                            line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
                            self.compute_line_ids_advice_amount_advance_org()

                            for x in self.account_payment_state_ids:
                                if x.advance_payment_id.id == yjzy_payment_id:
                                    x.amount_advance_balance_d = x.advance_payment_id.advance_balance_total
                                    x.reconcile_order_line_id = line.id

                    else:
                        line=line_obj.create({
                            'order_id': self.id,
                            'po_id': po.id,
                            'invoice_id': invoice.id,
                            'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                            'yjzy_payment_id': yjzy_payment_id,
                            'account_payment_state_id': account_payment_state_id
                        })
                        line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                        line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve

                        for x in self.account_payment_state_ids:
                            if x.advance_payment_id.id == yjzy_payment_id:
                                x.amount_advance_balance_d = x.advance_payment_id.advance_balance_total
                                x.reconcile_order_line_id = line.id

    #只创建一行
    def _make_lines_so_new(self):
        self.ensure_one()

        line_obj = self.env['account.reconcile.order.line']
        line_no_obj = self.env['account.reconcile.order.line.no']
        account_payment_state_obj = self.env['account.payment.state']
        if self.yjzy_advance_payment_id:
            yjzy_advance_payment_id = self.yjzy_advance_payment_id
        else:
            advance_payment_id = self.env.context.get('advance_payment_id') #从核销单上的预付单进行直接创建
            yjzy_advance_payment_id = self.env['account.payment'].search([('id','=',advance_payment_id)])
        account_payment_state_id = self.env.context.get('account_payment_state_id')
        print('yjzy_advance_payment_id_akiny',yjzy_advance_payment_id)
        print('le_akiny', len(self.line_ids), self.line_ids)
        for invoice in self.invoice_ids:
            po_invlines = self._prepare_sale_invoice_line(invoice)
            print('po_invline_akiny',po_invlines)
            if not po_invlines:
                line = line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for so, invlines in po_invlines.items():
                    if yjzy_advance_payment_id.so_id:
                        if so.id == yjzy_advance_payment_id.so_id.id:
                            yjzy_payment_id = yjzy_advance_payment_id.id
                        else:
                            yjzy_payment_id =False
                    else:
                        yjzy_payment_id = yjzy_advance_payment_id.id
                    #如果前端加了限制，这个就可以不用了

                    print('yjzy_payment_id_akiny',yjzy_payment_id)
                    lines_same_count = len(self.line_ids.filtered(lambda x: (x.yjzy_payment_id.id == yjzy_payment_id and x.invoice_id.id == invoice.id) or
                                                                            (x.yjzy_payment_id and not x.yjzy_payment_id.so_id)))
                    print('line_same_count_akiny',lines_same_count,invoice.id)
                    if yjzy_advance_payment_id.so_id:
                        if (so.id == yjzy_advance_payment_id.so_id.id and lines_same_count == 0):
                            line=line_obj.create({
                                'order_id': self.id,
                                'so_id': so.id,
                                'invoice_id': invoice.id,
                                'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                                'yjzy_payment_id':yjzy_payment_id,
                                'account_payment_state_id':account_payment_state_id
                            })
                            print('')
                            line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                            line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
                            self.compute_line_ids_advice_amount_advance_org()

                            for x in self.account_payment_state_ids:
                                if x.advance_payment_id.id == yjzy_payment_id:
                                    x.amount_advance_balance_d = x.advance_payment_id.advance_balance_total
                                    x.reconcile_order_line_id = line.id

                    else:
                        line=line_obj.create({
                            'order_id': self.id,
                            'so_id': so.id,
                            'invoice_id': invoice.id,
                            'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                            'yjzy_payment_id': yjzy_payment_id,
                            'account_payment_state_id': account_payment_state_id
                        })
                        line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                        line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve

                        for x in self.account_payment_state_ids:
                            if x.advance_payment_id.id == yjzy_payment_id:
                                x.amount_advance_balance_d = x.advance_payment_id.advance_balance_total
                                x.reconcile_order_line_id = line.id

    #line_ids计算建议预付认领
    def compute_line_ids_advice_amount_advance_org(self):
        for one in self.line_ids:
            if self.sfk_type == 'yshxd':
                amount_invoice_so = one.amount_invoice_so
                yuanze_advance_so = one.so_tb_percent * one.yjzy_payment_id.amount
                so_line_ids = self.line_ids.filtered(lambda x: x.so_id == one.so_id)
                print('po_line_ids_akiny', so_line_ids)
                lishi_hxd = one.yjzy_payment_id.advance_reconcile_order_line_ids
                amount_org_hxd = sum(x.amount_advance_org for x in lishi_hxd)

                if yuanze_advance_so - amount_org_hxd > 0:
                    advice_amount_advance_org_real = yuanze_advance_so - amount_org_hxd
                else:
                    advice_amount_advance_org_real = 0
                one.advice_amount_advance_org_real = advice_amount_advance_org_real


            elif self.sfk_type == 'yfhxd':
                amount_invoice_so = one.amount_invoice_so  #采购单对应的本次出运金额
                yuanze_advance_so = one.so_tb_percent * one.yjzy_payment_id.amount
                print('yuanze_advance_so_akiny',yuanze_advance_so)
                lishi_hxd = one.yjzy_payment_id.advance_reconcile_order_line_ids
                amount_org_hxd = sum(x.amount_advance_org for x in lishi_hxd)
                print('amount_org_hxd_akiny',amount_org_hxd)


                if yuanze_advance_so - amount_org_hxd > 0:
                    advice_amount_advance_org_real = yuanze_advance_so - amount_org_hxd
                else:
                    advice_amount_advance_org_real = 0
                #
                # least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total \
                #                                   - one.yjzy_payment_id.po_id.no_deliver_amount_new \
                #                                   - rest_amount_org_hxd  # 缺一个所有发票的未收金额

                    # 采购合同的所有的预付认领金额


                # po_line_ids = self.line_ids.filtered(lambda x: x.po_id == one.po_id and x.yjzy_payment_id == one.yjzy_payment_id) #所有采购单等于本次认领采购单的认领明细以及预付款单等于本次认领预付单
                # print('po_line_ids_akiny',po_line_ids)
                # so_amount_all = sum(x.amount_invoice_so for x in po_line_ids) #所有已经认领的明细的采购出运总和
                # amount_org_hxd = one.yjzy_payment_id.po_id.amount_org_hxd #采购合同的所有的预付认领金额
                # amount_po = one.yjzy_payment_id.po_id.amount_total
                # rest_amount_org_hxd = amount_po - amount_org_hxd
                # least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total \
                #                                   - one.yjzy_payment_id.po_id.no_deliver_amount_new \
                #                                   - rest_amount_org_hxd  # 缺一个所有发票的未收金额
                # if least_advice_amount_advance_org < 0:
                #     least_advice_amount_advance_org = 0
                one.advice_amount_advance_org_real = advice_amount_advance_org_real
                # one.least_advice_amount_advance_org = least_advice_amount_advance_org
                # print('werewrewrer______', one.yjzy_payment_id.advance_balance_total, one.advice_amount_advance_org)

    # line_ids计算建议预付认领
    def compute_line_ids_advice_amount_advance_org_old(self):
        for one in self.line_ids:
            if self.sfk_type == 'yshxd':
                print('werewrewrer', one.yjzy_payment_id.advance_balance_total)
                amount_invoice_so = one.amount_invoice_so
                so_line_ids = self.line_ids.filtered(lambda x: x.so_id == one.so_id)
                print('po_line_ids_akiny', so_line_ids)
                so_amount_all = sum(x.amount_invoice_so for x in so_line_ids)
                amount_org_hxd = one.yjzy_payment_id.so_id.amount_org_hxd
                amount_so = one.yjzy_payment_id.so_id.amount_total
                rest_amount_org_hxd = amount_so - amount_org_hxd
                least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total - one.yjzy_payment_id.so_id.no_sent_amount_new - rest_amount_org_hxd  # 缺一个所有发票的未收金额
                if least_advice_amount_advance_org < 0:
                    least_advice_amount_advance_org = 0
                one.advice_amount_advance_org_real = one.so_tb_percent * one.yjzy_payment_id.amount - \
                                                     one.amount_advance_org_self + one.duoyu_this_time_advice_advance_org \
                                                     * (amount_invoice_so / so_amount_all)
                one.least_advice_amount_advance_org = least_advice_amount_advance_org


            elif self.sfk_type == 'yfhxd':
                amount_invoice_so = one.amount_invoice_so  # 采购单对应的本次出运金额
                po_line_ids = self.line_ids.filtered(lambda x: x.po_id == one.po_id)  # 所有采购单等于本次认领采购单的认领明细
                print('po_line_ids_akiny', po_line_ids)
                so_amount_all = sum(x.amount_invoice_so for x in po_line_ids)  # 所有已经认领的明细的采购出运总和
                amount_org_hxd = one.yjzy_payment_id.po_id.amount_org_hxd  # 采购合同的所有的预付认领金额
                amount_po = one.yjzy_payment_id.po_id.amount_total
                rest_amount_org_hxd = amount_po - amount_org_hxd
                least_advice_amount_advance_org = one.yjzy_payment_id.advance_balance_total \
                                                  - one.yjzy_payment_id.po_id.no_deliver_amount_new \
                                                  - rest_amount_org_hxd  # 缺一个所有发票的未收金额
                if least_advice_amount_advance_org < 0:
                    least_advice_amount_advance_org = 0
                one.advice_amount_advance_org_real = one.so_tb_percent * one.yjzy_payment_id.amount - \
                                                     one.amount_advance_org_self + one.duoyu_this_time_advice_advance_org \
                                                     * (amount_invoice_so / so_amount_all)
                one.least_advice_amount_advance_org = least_advice_amount_advance_org
                print('werewrewrer______', one.yjzy_payment_id.advance_balance_total, one.advice_amount_advance_org)


    #
    # @api.onchange('line_ids')
    # def onchange_line_ids(self):
    #     invoice = self.line_ids.mapped('invoice_id')



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


            one.amount_advance = invoice_currency.compute(one.amount_advance_org, company_currency)
            one.amount_payment = payment_currency != False and payment_currency.compute(one.amount_payment_org, company_currency)
            one.amount_bank = bank_currency != False and bank_currency.compute(one.amount_bank_org, company_currency)
            one.amount_diff = diff_currency != False and diff_currency.compute(one.amount_diff_org, company_currency)
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

    @api.depends('so_id','po_id','so_id.balance_new','po_id.balance_new')
    def compute_advance_residual(self):
        for one in self:
            advance_residual = one.so_id.balance_new
            advance_residual2 = one.po_id.balance_new
            one.advance_residual = advance_residual
            one.advance_residual2 = advance_residual2

    def _get_default_currency_id(self):
        return self.invoice_currency_id

    def _compute_amount_invoice_so_proportion(self):
        for one in self:
            amount_invoice = one.invoice_id.amount_total
            amount_invoice_so =  one.amount_invoice_so


            if amount_invoice !=0:
                amount_invoice_so_proportion = amount_invoice_so / amount_invoice
            else:
                amount_invoice_so_proportion = 0

            #算法：要amount_invoice_so - po=我的所有的认领明细金额。= 所有已经审批完成以及付款完成的 所有的明细

            one.amount_invoice_so_proportion = amount_invoice_so_proportion

    @api.depends('amount_invoice_so','order_id','order_id.state_1','order_id.state_1','po_id','yjzy_payment_id')
    def compute_can_approve(self):
        for one in self:
            if one.order_id.sfk_type == 'yfhxd':
                amount_invoice_so = one.amount_invoice_so
                # amount_payment_can_approve_all = one.invoice_id.amount_payment_can_approve_all
                #认领后的金额：减掉的 是包括其他单子参与一起计算的金额。 如果只是自己的，那么就是认领前的减去认领后金额
                #增加字段：认领后金额
                reconcile_line_ids = self.env['account.reconcile.order.line'].search([('order_id.state', 'in', ['post', 'done']), ('po_id', '=', one.po_id.id),('invoice_id','=',one.invoice_id.id)])
                amount_payment_all = sum(x.amount_total_org_new for x in reconcile_line_ids)
                reconcile_line_done_ids = self.env['account.reconcile.order.line'].search(
                    [('order_id.state', 'in', ['done']), ('po_id', '=', one.po_id.id),('invoice_id','=',one.invoice_id.id)])
                amount_payment_done = sum(x.amount_total_org_new for x in reconcile_line_done_ids)
                amount_invoice_so_residual = amount_invoice_so - amount_payment_done
                amount_invoice_so_residual_can_approve = amount_invoice_so - amount_payment_all
                one.amount_invoice_so_residual = amount_invoice_so_residual
                one.amount_invoice_so_residual_can_approve = amount_invoice_so_residual_can_approve
            else:
                amount_invoice_so = one.amount_invoice_so
                # amount_payment_can_approve_all = one.invoice_id.amount_payment_can_approve_all
                # 认领后的金额：减掉的 是包括其他单子参与一起计算的金额。 如果只是自己的，那么就是认领前的减去认领后金额
                # 增加字段：认领后金额
                reconcile_line_ids = self.env['account.reconcile.order.line'].search(
                    [('order_id.state', 'in', ['post', 'done']), ('so_id', '=', one.so_id.id),
                     ('invoice_id', '=', one.invoice_id.id)])
                amount_payment_all = sum(x.amount_total_org_new for x in reconcile_line_ids)
                reconcile_line_done_ids = self.env['account.reconcile.order.line'].search(
                    [('order_id.state', 'in', ['done']), ('so_id', '=', one.so_id.id),
                     ('invoice_id', '=', one.invoice_id.id)])
                amount_payment_done = sum(x.amount_total_org_new for x in reconcile_line_done_ids)
                amount_invoice_so_residual = amount_invoice_so - amount_payment_done
                amount_invoice_so_residual_can_approve = amount_invoice_so - amount_payment_all
                one.amount_invoice_so_residual = amount_invoice_so_residual
                one.amount_invoice_so_residual_can_approve = amount_invoice_so_residual_can_approve





    @api.depends('yjzy_payment_id','payment_currency_id','yjzy_payment_id.currency_id')
    def _compute_yjzy_currency_id(self):
        for one in self:
            if not one.yjzy_payment_id:
                one.yjzy_currency_id = one.payment_currency_id
            else:
                one.yjzy_currency_id = one.yjzy_payment_id.currency_id
    @api.depends('order_id.state','invoice_currency_id','payment_currency_id','currency_id','amount_advance_org','amount_payment_org')
    def compute_amount_total_org_new(self):
        for one in self:
            # date = one.order_id.date
            # # invoice_currency = one.invoice_currency_id.with_context(date=date)
            # # payment_currency = one.payment_currency_id.with_context(date=date)
            # # company_currency = one.currency_id.with_context(date=date)
            # # one.amount_advance = invoice_currency.compute(one.amount_advance_org, company_currency)
            # # one.amount_payment = payment_currency != False and payment_currency.compute(one.amount_payment_org, company_currency)
            amount_total_org_new = one.amount_advance_org + one.amount_payment_org

            one.amount_total_org_new = amount_total_org_new
            # one.amount_total = one.amount_advance + one.amount_payment

    #计算原始的剩余未发货金额，集中再一个字段上 计算出原始销售采购金额和剩余的销售采购金额，用剩余的是最新的算法。算建议认领预收和预付
    @api.depends('so_id','so_id.amount_total','so_id.no_sent_amount_new','amount_invoice_so','po_id.amount_total','po_id.no_deliver_amount_new','po_id')
    def compute_amount_so(self):
        for one in self:
            if one.order_id.sfk_type == 'yshxd':
                one.amount_so = one.so_id.amount_total
                one.no_delivery_amount_so = one.so_id.no_sent_amount_new + one.amount_invoice_so
            elif one.order_id.sfk_type == 'yfhxd':
                one.amount_so = one.po_id.amount_total
                one.no_delivery_amount_so = one.po_id.no_deliver_amount_new + one.amount_invoice_so
            print('one.no_delivery_amount_so',one.order_id.sfk_type,one.no_delivery_amount_so,one.so_id.no_sent_amount_new,  one.amount_invoice_so)


    #原来计算的是出运占销售金额的比例，现在改成出运占销售剩余金额的比例
    @api.depends('amount_invoice_so','amount_so','no_delivery_amount_so','order_id.yjzy_advance_payment_id.amount','order_id.yjzy_advance_payment_id','order_id')
    def compute_so_tb_percent(self):
        for one in self:
            amount_invoice_so = one.amount_invoice_so
            amount_so = one.amount_so
            no_delivery_amount_so = one.no_delivery_amount_so
            so_tb_percent = 0.0
            advice_amount_advance_org = 0
            if one.order_id.sfk_type == 'yshxd':
                if one.so_id and amount_so != 0:
                    so_tb_percent = amount_invoice_so / amount_so
                    # so_tb_percent = amount_invoice_so / no_delivery_amount_so
                else:
                    so_tb_percent = 0.0
                advice_amount_advance_org = so_tb_percent * one.order_id.yjzy_advance_payment_id.amount
            if one.order_id.sfk_type == 'yfhxd':
                if one.po_id and amount_so != 0:
                    so_tb_percent = amount_invoice_so / amount_so
                    # so_tb_percent = amount_invoice_so / no_delivery_amount_so
                else:
                    so_tb_percent = 0.0
                advice_amount_advance_org = so_tb_percent * one.order_id.yjzy_advance_payment_id.amount
            one.so_tb_percent = so_tb_percent
            one.advice_amount_advance_org = advice_amount_advance_org


    def compute_ysrld_amount_advance_org_all(self):
        for one in self:
            invoice_ids = one.order_id.invoice_ids # （自己原则-自己认领）+（其他原则-其他认领）（这个其他是本次认领的所有发票的其他，不是这次进行认领的）这个多余的要给这次认领的所有的发票的采购进行比较分配
            hxd_ids = one.yjzy_payment_id.advance_reconcile_order_line_ids.filtered(lambda x: x.invoice_id not in invoice_ids and x.amount_advance_org !=0 and x.order_id.state == 'done')
            hxd_self_ids = one.yjzy_payment_id.advance_reconcile_order_line_ids.filtered(lambda x:x.invoice_id == one.invoice_id and x.amount_advance_org !=0  and x.order_id.state =='done')#不等于0 是因为 老的数据，只要符合po相yjzy_payent同，就会给明细加上等于当前发票的核销单

            line_obj = self.env['account.reconcile.order.line']
            # amount_advance_org_all = sum(x.amount_advance_org for x in hxd_ids)
            lines = line_obj.browse([])
            dic = {}
            for i in hxd_ids:
                invoice = i.invoice_id
                k = invoice.id
                if k not in dic:
                    print('k', k)
                    dic[k] = {'invoice_id': invoice.id,
                              }
                    lines |= i


            ysrld_amount_advance_org_all = sum(x.amount_advance_org for x in hxd_ids)
            ysrld_advice_amount_advance_org_all = sum(x.advice_amount_advance_org_real for x in lines)#ok # 之前是没有real的，计算错误，现在改成real

            amount_advance_org_self = sum(x.amount_advance_org for x in hxd_self_ids)

            duoyu_this_time_advice_advance_org = ysrld_advice_amount_advance_org_all - ysrld_amount_advance_org_all
            one.ysrld_amount_advance_org_all= ysrld_amount_advance_org_all
            one.ysrld_advice_amount_advance_org_all = ysrld_advice_amount_advance_org_all
            one.amount_advance_org_self = amount_advance_org_self
            one.duoyu_this_time_advice_advance_org = duoyu_this_time_advice_advance_org

            print('lines______111111111',lines)



            # ysrld_amount_advance_org_all = one.yjzy_advance_payment_id.amount_advance_org_all
            # ysrld_advice_amount_advance_org_all = one.yjzy_advance_payment_id.advice_amount_advance_org_all
            # duoyu_this_time_advice_advance_org = ysrld_advice_amount_advance_org_all - ysrld_amount_advance_org_all
            # print('duoyu_this_time_advice_advance_org', duoyu_this_time_advice_advance_org)
            # one.ysrld_amount_advance_org_all = ysrld_amount_advance_org_all
            # one.ysrld_advice_amount_advance_org_all = ysrld_advice_amount_advance_org_all
            # one.duoyu_this_time_advice_advance_org = duoyu_this_time_advice_advance_org

    @api.depends('invoice_id', 'invoice_id.amount_total')
    def compute_amount_total_invoice(self):
        for one in self:
            one.amount_total_invoice = one.invoice_id.amount_total

    @api.depends('amount_invoice_so_residual_can_approve_d','amount_total_org_new','amount_invoice_so_residual_d')
    def compute_amount_invoice_so_residual_can_approve_d_after(self):
        for x in self:
            amount_invoice_so_residual_can_approve_d = x.amount_invoice_so_residual_can_approve_d
            amount_total_org_new = x.amount_total_org_new
            amount_invoice_so_residual_d = x.amount_invoice_so_residual_d
            x.amount_invoice_so_residual_can_approve_d_after = amount_invoice_so_residual_can_approve_d - amount_total_org_new
            x.amount_invoice_so_residual_d_after = amount_invoice_so_residual_d - amount_total_org_new


    invoice_move_line_com_yfzk_ids_count = fields.Integer('账单付款日志数量',related='invoice_id.move_line_com_yfzk_ids_count')
    invoice_move_line_com_yszk_ids_count = fields.Integer('账单收款日志数量',related='invoice_id.move_line_com_yszk_ids_count')
    invoice_move_line_com_yfzk_ids = fields.One2many('account.move.line.com','应付账单日志',related='invoice_id.move_line_com_yfzk_ids')
    invoice_move_line_com_yszk_ids = fields.One2many('account.move.line.com', '应收账单日志',
                                                     related='invoice_id.move_line_com_yszk_ids')
    invoice_reconcile_order_ids = fields.Many2many('account.reconcile.order',related='invoice_id.reconcile_order_ids')
    invoice_reconcile_order_ids_count = fields.Integer(u'核销单据数量',related='invoice_id.reconcile_order_ids_count')
    invoice_reconcile_order_line_no_ids = fields.One2many('account.reconcile.order.line.no', related='invoice_id.reconcile_order_line_no_ids')
    invoice_reconcile_order_line_no_ids_count = fields.Integer(u'no数量',related='invoice_id.reconcile_order_line_no_ids_count')

    hxd_type_new = fields.Selection('认领来源',related='order_id.hxd_type_new')

    yingshouyingfurld_ids = fields.One2many('account.payment', 'account_reconcile_order_line_id', '生成的应收应付认领单')

    account_payment_state_id = fields.Many2one('account.payment.state','本次认领的预付记录', ondelete='cascade')

    least_advice_amount_advance_org = fields.Monetary(u'最低建议金额',currency_field='yjzy_currency_id')

    ysrld_amount_advance_org_all = fields.Float('预收单的本所有非本账单采购的被认领金额', compute=compute_ysrld_amount_advance_org_all)
    ysrld_advice_amount_advance_org_all = fields.Float('预收认领单的非本账单采购的被认领的原则分配金额',
                                                       compute=compute_ysrld_amount_advance_org_all)
    amount_advance_org_self = fields.Float('自己的所有的认领金额',compute=compute_ysrld_amount_advance_org_all)
    duoyu_this_time_advice_advance_org = fields.Float('多余的预收付这次应该加上的认领金额', compute=compute_ysrld_amount_advance_org_all)



    # @api.onchange('amount_invoice_so', 'amount_advance_org', 'amount_bank_org', 'amount_diff_org', 'amount_payment_org')
    # def onchange_amount(self):
    #     self.amount_exchange_org = self.amount_invoice_so - self.amount_advance_org - self.amount_bank_org - self.amount_diff_org - self.amount_payment_org
    advice_amount_advance_org = fields.Monetary(u'建议预收金额', currency_field='yjzy_currency_id',compute=compute_so_tb_percent, store=True)#原则上的分配金额，就是销售采购占原始比例*原始的预收预付金额
    advice_amount_advance_org_real = fields.Monetary(u'实际建议预收金额',currency_field='yjzy_currency_id')
    date = fields.Date('日期',related="order_id.date")
    state_1 = fields.Selection('审批流程',related='order_id.state_1')
    order_id = fields.Many2one('account.reconcile.order', u'核销单',ondelete='cascade')
    partner_type = fields.Selection(related='order_id.partner_type')
    payment_type = fields.Selection(related='order_id.payment_type')
    approve_date = fields.Date(u'审批完成时间', related='order_id.approve_date')
    so_id = fields.Many2one('sale.order', u'销售单')
    so_contract_code = fields.Char(u'销售合同号', related='so_id.contract_code', readonly=True)

    invoice_display_name =  fields.Char('发票显示名字', related='invoice_id.display_name' , store=True)

    sfk_type = fields.Selection( u'收付类型', related='order_id.sfk_type')
    po_id = fields.Many2one('purchase.order', u'采购单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    yjzy_invoice_id = fields.Many2one('account.invoice', u'发票关联账单', related='invoice_id.yjzy_invoice_id')  # 额外账单的认领明细
    invoice_attribute = fields.Selection(related='invoice_id.invoice_attribute', string=u'账单类型')
    tb_contract_code = fields.Char('出运合同号', related='invoice_id.tb_contract_code', readonly=True)
    residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True, currency_field='invoice_currency_id')
    amount_total_invoice = fields.Monetary(u'发票原始金额',compute=compute_amount_total_invoice, readonly=True,
                               currency_field='invoice_currency_id',store=True)

    currency_id = fields.Many2one('res.currency', u'公司货币', related='order_id.currency_id', readonly=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='order_id.payment_currency_id', readonly=True)


    ##银行扣款和销售费用的货币随收款货币；
    # bank_currency_id = fields.Many2one('res.currency', related='order_id.bank_currency_id', )
    # diff_currency_id = fields.Many2one('res.currency', related='order_id.diff_currency_id', )

    amount_invoice_so = fields.Monetary(u'合计', currency_field='invoice_currency_id')
    amount_so = fields.Monetary(u'原始销售金额',currency_field='invoice_currency_id',compute=compute_amount_so,store=True)
    no_delivery_amount_so = fields.Monetary(u'未发货销售或者采购金额', currency_field='invoice_currency_id', compute=compute_amount_so, store=True)
    so_tb_percent = fields.Float(u'出运占原销售采购金额的比例',compute=compute_so_tb_percent,store=True) #原则上的比例


    amount_invoice_so_proportion = fields.Float('销售金额占发票金额比',compute=_compute_amount_invoice_so_proportion)
    #826
    amount_invoice_so_residual = fields.Monetary(u'占比剩余应收付',currency_field='invoice_currency_id',compute=compute_can_approve)
    amount_invoice_so_residual_d = fields.Monetary(u'静态占比剩余应收付',currency_field='invoice_currency_id')#认领前
    amount_invoice_so_residual_d_after = fields.Monetary(u'本次认领后可认领金额',currency_field='invoice_currency_id',compute=compute_amount_invoice_so_residual_can_approve_d_after)
    amount_invoice_so_residual_can_approve = fields.Monetary(u'占比剩余可申请的应收付',currency_field='invoice_currency_id',compute=compute_can_approve)
    amount_invoice_so_residual_can_approve_d = fields.Monetary(u'静态占比剩余可申请的应收付',currency_field='invoice_currency_id')
    amount_invoice_so_residual_can_approve_d_after = fields.Monetary(u'本次认领后可申请金额', currency_field='invoice_currency_id',compute=compute_amount_invoice_so_residual_can_approve_d_after)
    advance_residual = fields.Monetary(currency_field='yjzy_currency_id', string=u'预付余额', compute=compute_advance_residual, store=True)
    advance_residual2 = fields.Monetary(currency_field='yjzy_currency_id', string=u'预收余额', compute=compute_advance_residual, store=True)

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
    amount_total_org_new = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_amount_total_org_new,store=True)

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment_id(self):
        print('yjzy_currency_id',self.yjzy_currency_id)
        self.yjzy_currency_id = self.yjzy_payment_id.currency_id



# class reconcile_order_line_related(models.Model):
#     _name = 'reconcile.order.line.related'
#
#     order_line_id = fields.Many2one('account.reconcile.order.line',u'预收付认领明细')
#     order_id = fields.Many2one('account.reconcile.order','核销单',ondelete='cascade')
#     yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='order_line_id.yjzy_currency_id')
#     least_advice_amount_advance_org = fields.Monetary(u'最低建议金额',currency_field='yjzy_currency_id',related='order_line_id.least_advice_amount_advance_org')
#
#     advice_amount_advance_org = fields.Monetary(u'建议预收金额', currency_field='yjzy_currency_id',related='order_line_id.advice_amount_advance_org')#原则上的分配金额，就是销售采购占原始比例*原始的预收预付金额
#     advice_amount_advance_org_real = fields.Monetary(u'实际建议预收金额',currency_field='yjzy_currency_id',related='order_line_id.advice_amount_advance_org_real')
#
#     so_id = fields.Many2one('sale.order', u'销售单',related='order_line_id.so_id')
#     po_id = fields.Many2one('purchase.order', u'采购单',related='order_line_id.po_id')
#     tb_contract_code = fields.Char('出运合同号', related='order_line_id.tb_contract_code', readonly=True)
#
#     currency_id = fields.Many2one('res.currency', u'公司货币', related='order_line_id.currency_id', readonly=True)
#     invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='order_line_id.invoice_currency_id', readonly=True)
#     payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='order_line_id.payment_currency_id', readonly=True)
#
#
#     amount_invoice_so = fields.Monetary(u'合计', currency_field='invoice_currency_id',related='order_line_id.amount_invoice_so')
#     amount_so = fields.Monetary(u'原始销售金额',currency_field='invoice_currency_id',related='order_line_id.amount_so')
#
#     #826
#     amount_invoice_so_residual = fields.Monetary(u'占比剩余应收付',currency_field='invoice_currency_id',related='order_line_id.amount_invoice_so_residual')
#     amount_invoice_so_residual_can_approve = fields.Monetary(u'占比剩余可申请的应收付',currency_field='invoice_currency_id',related='order_line_id.amount_invoice_so_residual_can_approve')
#
#     company_id =  fields.Many2one('res.company', string=u'公司', related='order_id.company_id')
#
#     yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单',related='order_line_id.yjzy_payment_id')
#     amount_advance_org = fields.Monetary(u'预收金额', currency_field='yjzy_currency_id',related='order_line_id.amount_advance_org')

    def open_invoice_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_rizhi').id
        return {'name':'账单查看',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'views': [(form_view, 'form')],
                'res_id': self.invoice_id.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                # 'flags': {'sidebar': False,  #参考flag
                #           'initial_mode': 'read',
                #     'form': {
                #         'action_buttons': False,
                #          'initial_mode': 'read',
                #          'options': {'mode': 'view'},
                #     }},

                 'context': {'open':1}
                }


class account_reconcile_order_line_no(models.Model):
    _name = 'account.reconcile.order.line.no'


    @api.depends('amount_payment_can_approve_all_this_time','invoice_residual_this_time','amount_payment_org')
    def compute_amount_payment_can_approve_all_after(self):
        for line in self:
            line_ids_line = line.order_id.line_ids.filtered(lambda x: x.invoice_id == line.invoice_id)#本条发票未拆分明细对应的拆分明细
            # advance_amount_org = sum(x.amount_advance_org for x in line_ids_line)
            advance_amount_org = line.amount_advance_org_compute
            amount_payment_can_approve_all_this_time = line.amount_payment_can_approve_all_this_time
            amount_payment_org = line.amount_payment_org
            invoice_residual_this_time = line.invoice_residual_this_time
            line.amount_payment_can_approve_all_after = amount_payment_can_approve_all_this_time - amount_payment_org - advance_amount_org#再减去line_ids里面对应的预付认领的金额。其实可以把amount_payment_org也可以从line_ids计算
            line.invoice_residual_after = invoice_residual_this_time - amount_payment_org


    @api.depends('order_id.line_ids','order_id.line_ids.amount_advance_org')
    def compute_amount_advance_org_compute(self):
        for one in self:
            line_ids = one.order_id.line_ids.filtered(lambda x: x.invoice_id == one.invoice_id)
            amount_advance_org_compute = sum(x.amount_advance_org for x in line_ids)
            amount_payment_org = one.amount_payment_org
            one.amount_advance_org_compute = amount_advance_org_compute
            one.amount_total_org = amount_advance_org_compute + amount_payment_org

    @api.depends('invoice_id','invoice_id.invoice_attribute_all_in_one')
    def compute_invoice_id(self):
        for one in self:
            invoice_id = one.invoice_id
            one.invoice_attribute_all_in_one = invoice_id.invoice_attribute_all_in_one

    #计算出非自己认领明细原则
#1220

    hxd_type_new = fields.Selection('认领来源',related='order_id.hxd_type_new')
    yingshouyingfurld_ids = fields.One2many('account.payment', 'account_reconcile_order_line_no_id', '生成的应收应付认领单')
    amount_total_org = fields.Monetary('总认领金额',currency_field='invoice_currency_id',compute=compute_amount_advance_org_compute, store=True)
    fkzl_id = fields.Many2one('account.payment',u'付款指令')

    ysrld_amount_advance_org_all = fields.Float('预收单的本所有非本账单采购的被认领金额',)
    ysrld_advice_amount_advance_org_all = fields.Float('预收认领单的非本账单采购的被认领的原则分配金额',)
    duoyu_this_time_advice_advance_org = fields.Float('多余的预收付这次应该加上的认领金额',)

    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)

    state_1 = fields.Selection('审批流程', related='order_id.state_1')
    order_id = fields.Many2one('account.reconcile.order', u'核销单',ondelete='cascade')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    invoice_invoice_partner = fields.Char(u'账单对象',related='invoice_id.invoice_partner')
    invoice_name_title =fields.Char(u'账单描述',related='invoice_id.name_title')

    invoice_attribute_all_in_one = fields.Selection(invoice_attribute_all_in_one,u'账单属性all_in_one', compute=compute_invoice_id,store=True)

    yjzy_invoice_id = fields.Many2one('account.invoice', u'发票关联账单', related='invoice_id.yjzy_invoice_id')  # 额外账单的认领明细
    approve_date = fields.Date(u'审批完成时间',related='order_id.approve_date')



    invoice_id_po_ids = fields.Many2many('purchase.order',related='invoice_id.po_ids')

    invoice_residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True, currency_field='invoice_currency_id')
    residual = fields.Monetary(related='invoice_id.residual', string=u'发票余额', readonly=True,
                               currency_field='invoice_currency_id') #有一个没用
    invoice_amount_total = fields.Monetary(related='invoice_id.amount_total', string=u'发票金额', readonly=True, currency_field='invoice_currency_id')
    amount_payment_can_approve_all = fields.Monetary(related='invoice_id.amount_payment_can_approve_all',string='可以申请支付应付款')
    amount_payment_can_approve_all_this_time = fields.Monetary(u'可以申请支付应付款d',currency_field='invoice_currency_id')

    invoice_residual_this_time = fields.Monetary( string=u'发票余额d', readonly=True,currency_field='invoice_currency_id')

    amount_payment_can_approve_all_after = fields.Monetary(u'本次申请后可申请金额', currency_field='invoice_currency_id',
                                                           compute=compute_amount_payment_can_approve_all_after)

    invoice_residual_after = fields.Monetary(string=u'本次认领后可认领金额', readonly=True, currency_field='invoice_currency_id',compute=compute_amount_payment_can_approve_all_after)



    reconcile_order_line_payment = fields.Monetary(related='invoice_id.reconcile_order_line_payment', string=u'发票付款支付',
                                                   readonly=True)


    reconcile_order_line_advance = fields.Monetary(related='invoice_id.reconcile_order_line_advance', string=u'发票预付认领',
                                                   readonly=True)

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


    amount_advance_org_compute = fields.Monetary(u'计算的预收预付金额', currency_field='yjzy_currency_id',compute=compute_amount_advance_org_compute,)
    amount_advance_org = fields.Monetary(u'预收金额', currency_field='yjzy_currency_id')
    advice_amount_advance_org = fields.Monetary(u'建议预收金额', currency_field='yjzy_currency_id')
    least_advice_amount_advance_org = fields.Monetary(u'最低建议金额',currency_field='yjzy_currency_id')


    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单')
    yjzy_payment_po_id = fields.Many2one('purchase.order',related='yjzy_payment_id.po_id',string='预付采购')

    amount_advance = fields.Monetary(u'预收金额:本币', currency_field='currency_id' )
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='payment_currency_id')
    amount_payment = fields.Monetary(u'收款金额:本币', currency_field='currency_id', )

    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='payment_currency_id')
    amount_diff_org = fields.Monetary(u'订单费用', currency_field='payment_currency_id')


    def open_invoice_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_invoice_rizhi').id
        return {'name':'查看日志',
                'view_type': 'form',
                'view_mode': 'form',
                'res_model': 'account.invoice',
                'views': [(form_view, 'form')],
                'res_id': self.invoice_id.id,
                'target': 'new',
                'type': 'ir.actions.act_window',
                 'context': {}
                }





#本次认领前后的预付款的记录情况
class advance_payment_state(models.Model):
    _name = 'account.payment.state'

    def compute_info(self):
        for one in self:
            advance_payment_currency = one.advance_payment_id.yjzy_payment_currency_id
            amount_advance_balance = one.advance_payment_id.advance_balance_total
            amount_payment = one.advance_payment_id.amount
            one.advance_payment_currency = advance_payment_currency
            one.amount_advance_balance = amount_advance_balance
            one.amount_payment = amount_payment

    @api.depends('reconcile_order_line_ids','reconcile_order_line_ids.amount_advance_org','amount_advance_balance_d')
    def compute_amount_reconcile(self):
        for one in self:
            amount_reconcile_old = one.reconcile_order_line_id.amount_total_org_new
            amount_reconcile = sum(x.amount_advance_org for x in one.reconcile_order_line_ids)
            amount_advance_balance_d = one.amount_advance_balance_d
            one.amount_reconcile = amount_reconcile
            one.amount_advance_balance_after = amount_advance_balance_d - amount_reconcile

    # line_ids = fields.One2many('account.reconcile.order.line','account_payment_state_id',u'关联的明细行')
    advance_payment_id = fields.Many2one('account.payment',u'预收付款单',ondelete='cascade')
    reconcile_order_id = fields.Many2one('account.reconcile.order','认领单',ondelete='cascade')#手动写进来
    advance_payment_date = fields.Date('付款日期',related='advance_payment_id.payment_date')
    po_id = fields.Many2one('purchase.order',related='advance_payment_id.po_id')
    so_id = fields.Many2one('sale.order',related='advance_payment_id.so_id')
    reconcile_order_line_id = fields.Many2one('account.reconcile.order.line','认领明细')  #错误：认领明细是一对多的关系。。
    reconcile_order_line_ids = fields.One2many('account.reconcile.order.line','account_payment_state_id',u'认领明细')
    amount_payment = fields.Monetary(u'预收付款单余额',currency_field='advance_payment_currency',compute=compute_info)
    amount_advance_balance = fields.Monetary(u'预收付款单余额',currency_field='advance_payment_currency',compute=compute_info)
    advance_payment_currency = fields.Many2one('res.currency',compute=compute_info)
    company_id =  fields.Many2one('res.company', string=u'公司', related='reconcile_order_id.company_id')
    amount_advance_balance_d = fields.Monetary(u'本次认领前可认领金额',currency_field='advance_payment_currency',)
    amount_advance_balance_after = fields.Monetary(u'本次认领后可认领金额',currency_field='advance_payment_currency',compute=compute_amount_reconcile,store=True)
    amount_reconcile = fields.Monetary(u'本次认领金额',currency_field='advance_payment_currency',compute=compute_amount_reconcile,store=True)
    state_1 = fields.Selection('审批流程',related='reconcile_order_id.state_1')
    state = fields.Selection([('reconcile','认领'),('no_reconcile','未认领')],u'认领状态',default='no_reconcile')




    # renling = fields.Boolean('认领')
    #
    # @api.onchange('renling')
    # def onchange_renling(self):
    #     print('renling_akiny',self.renling)
    #     renling = self.renling
    # # if renling:
    #     print('renling_akiny2', renling)
    #     self.action_make_reconcile_line_ids()
    #     # else:
    #     #     print('renling_akiny3', renling)
    #     #     self.action_cancel_reconcile_line_ids()

    def action_make_reconcile_line_ids(self):
        ctx_hxd = self.env.context.get('hxd_id')
        hxd_id = self.reconcile_order_id
        print('hxd_id_akiny',hxd_id.id)
        hxd_id.with_context({'advance_payment_id': self.advance_payment_id.id,
                             'account_payment_state_id':self.id}).make_lines_11_16()
        self.state = 'reconcile'
        # self.amount_advance_balance_d = self.advance_payment_id.advance_balance_total

    #ok_1218   1220
    def action_add_yjzy_payment_id(self):
        hxd_id = self.reconcile_order_id
        line_ids = hxd_id.line_ids
        advance_payment_id = self.advance_payment_id
        account_payment_state_id = self
        yjzy_payment_id_lines = line_ids.mapped('yjzy_payment_id')

        if hxd_id.sfk_type == 'yfhxd':
            if advance_payment_id.id not in yjzy_payment_id_lines.ids:
                self._make_lines_po()
                # line_do_ids= hxd_id.line_ids.filtered(lambda x: x.yjzy_payment_id.id != False)
                # print('line_do_ids_akiny',line_do_ids)
                # hxd_id.line_do_ids = line_do_ids
                hxd_id.compute_line_ids_advice_amount_advance_org()


        if hxd_id.sfk_type == 'yshxd':
            if advance_payment_id.id not in yjzy_payment_id_lines.ids:
                self._make_lines_so()
                # line_do_ids = self.env['account.reconcile.order.line'].search(
                #     [('yjzy_payment_id', '!=', False), ('order_id', '=', hxd_id.id)])
                # line_do_ids = hxd_id.line_ids.filtered(lambda x: x.yjzy_payment_id.id != False)
                # print('line_do_ids_akiny', line_do_ids)
                # hxd_id.line_do_ids = line_do_ids
                hxd_id.compute_line_ids_advice_amount_advance_org()
                print('yjzy_payment_id_akiny_1',self.reconcile_order_id.yjzy_payment_id)
                if not self.reconcile_order_id.yjzy_payment_id:
                    self.reconcile_order_id.hxd_type_new = '10'
                    self.reconcile_order_id.operation_wizard = '20'
                else:
                    self.reconcile_order_id.hxd_type_new = '25'
                    self.reconcile_order_id.operation_wizard = '30'
        self.state = 'reconcile'

    def action_cancel_reconcile_line_ids(self):
        reconcile_order_line_ids = self.reconcile_order_line_ids
        reconcile_order_line_ids.unlink() #取消的时候讲line相关的删除
        self.state = 'no_reconcile'
        self.compute_amount_reconcile()
        if not self.reconcile_order_id.yjzy_payment_id:
            self.reconcile_order_id.hxd_type_new = '10'
            self.reconcile_order_id.operation_wizard = '20'
        else:
            print('line_ids_akiny',self.reconcile_order_id.line_ids)
            if not self.reconcile_order_id.line_ids:
                self.reconcile_order_id.hxd_type_new = '20'
                self.reconcile_order_id.operation_wizard = '10'


    def action_remove_reconcile_line_ids(self):
        hxd_id = self.reconcile_order_id
        hxd_id = self.reconcile_order_id
        if hxd_id.line_ids:
            for one in hxd_id.line_ids:
                if one.yjzy_payment_id == self.advance_payment_id:
                    one.unlink()

        if hxd_id.line_no_ids:
            for one in hxd_id.line_no_ids:
                if one.yjzy_payment_id == self.advance_payment_id:
                    one.unlink()
        self.state = 'no_reconcile'
        # self.amount_advance_balance_d = 0.0
        self.compute_amount_reconcile()

    #1220
    def _make_lines_po(self):
        self.ensure_one()
        order_id = self.reconcile_order_id
        invoice_ids = order_id.invoice_ids
        po_id = self.advance_payment_id.po_id
        line_ids = order_id.line_ids
        if not po_id and line_ids:
            raise Warning('已经有存在认领的明细，不允许再添加没有采购合同的预付单！')
        line_obj = self.env['account.reconcile.order.line']
        for invoice in invoice_ids:
            po_invlines = self._prepare_purchase_invoice_line(invoice)
            if not po_invlines:
                line = line_obj.create({
                    'order_id': order_id.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })

                self.reconcile_order_id.write({'line_do_ids': [(4, line.id)]})
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for po, invlines in po_invlines.items():
                    if po_id:
                        if po.id == po_id.id:
                            yjzy_payment_id = self.advance_payment_id.id
                        else:
                            yjzy_payment_id = False
                    else:
                        yjzy_payment_id = self.advance_payment_id.id
                    line = line_obj.create({
                        'order_id': order_id.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'yjzy_payment_id': yjzy_payment_id,
                        'account_payment_state_id':self.id
                    })
                    print('yjzy_payment_id_akiny', yjzy_payment_id)
                    if yjzy_payment_id != False:
                        self.reconcile_order_id.write({'line_do_ids': [(4, line.id)]})
                    line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                    line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve

        if not order_id.line_no_ids:
            order_id.make_line_no()

    # 1220
    def _make_lines_so(self):
        self.ensure_one()
        order_id = self.reconcile_order_id
        invoice_ids = order_id.invoice_ids
        so_id = self.advance_payment_id.so_id
        line_ids = order_id.line_ids
        if not so_id and line_ids:
            raise Warning('已经有存在认领的明细，不允许再添加没有销售合同的预收单！')
        line_obj = self.env['account.reconcile.order.line']
        for invoice in invoice_ids:
            po_invlines = self._prepare_sale_invoice_line(invoice)
            if not po_invlines:
                line = line_obj.create({
                    'order_id': order_id.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
                self.reconcile_order_id.write({'line_do_ids': [(4, line.id)]})
                line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve
            else:
                for so, invlines in po_invlines.items():
                    if so_id:
                        if so.id == so_id.id:
                            yjzy_payment_id = self.advance_payment_id.id
                        else:
                            yjzy_payment_id = False
                    else:
                        yjzy_payment_id = self.advance_payment_id.id
                    line = line_obj.create({
                        'order_id': order_id.id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                        'yjzy_payment_id': yjzy_payment_id,
                        'account_payment_state_id': self.id
                    })
                    print('yjzy_payment_id_akiny',yjzy_payment_id,so_id,self.advance_payment_id)
                    if yjzy_payment_id:
                        self.reconcile_order_id.write({'line_do_ids':[(4,line.id)]})
                    line.amount_invoice_so_residual_d = line.amount_invoice_so_residual
                    line.amount_invoice_so_residual_can_approve_d = line.amount_invoice_so_residual_can_approve

        if not order_id.line_no_ids:
            order_id.make_line_no()

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

    def open_yfsqd(self):
        form_view = self.env.ref('yjzy_extend.view_yfsqd_form_open')
        return {'name': u'预付款申请单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'views': [ (form_view.id, 'form')],
            'res_id': self.advance_payment_id.id,
            'target':'new',
            'context': {'display_name_code':1,
                        'open':1
                        }}

    def open_ysqd(self):
        form_view = self.env.ref('yjzy_extend.view_ysrld_form_new_open')
        return {'name': u'预收认领单',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.payment',
            'views': [ (form_view.id, 'form')],
            'res_id': self.advance_payment_id.id,
            'target':'new',
            'context': {'display_name_code':1,
                        'open':1
                        }}

    def open_wizard_renling_ysrld(self):
        self.ensure_one()
        ctx = self.env.context.copy()
        invoice_ids = self.reconcile_order_id.invoice_ids
        wizard_obj = self.env['wizard.renling.ysrld']
        if self.so_id:
            ctx.update({
                'default_so_id': self.so_id.id,
                'default_partner_id': self.reconcile_order_id.partner_id.id,
                'default_yjzy_advance_payment_id': self.advance_payment_id.id,
                'default_invoice_ids': invoice_ids.ids,
                'default_invoice_attribute':self.reconcile_order_id.invoice_attribute,
                'default_yjzy_type':self.reconcile_order_id.yjzy_type,
                'default_invoice_type_main':self.reconcile_order_id.invoice_type_main,
            })
        else:
            ctx.update({
                'default_partner_id': self.reconcile_order_id.partner_id.id,
                'default_yjzy_advance_payment_id': self.advance_payment_id.id,
                'default_invoice_ids':invoice_ids.ids,
                'default_invoice_attribute': self.reconcile_order_id.invoice_attribute,
                'default_yjzy_type': self.reconcile_order_id.yjzy_type,
                'default_invoice_type_main': self.reconcile_order_id.invoice_type_main,
            })

        wizard = wizard_obj.with_context(ctx).create()

        form_view = self.env.ref('yjzy_extend.wizard_renling_ysrld_form')
        return {
            'name': '创建认领',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.renling.ysrld',
            'views': [(form_view.id, 'form')],
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }



#------------------1220 更新说明
#预收预付全部都要创建payment.state
#明细行的创建全部从payment.state创建
#给预收付state加上make_line_po的函数
#没有po和so的预收预付，必须单独认领
#line_no单独创建，收款付款认领或者同时认领的时候


