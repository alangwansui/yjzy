# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from .comm import sfk_type
import logging

_logger = logging.getLogger(__name__)


class account_reconcile_order(models.Model):
    _name = 'account.reconcile.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '核销单'
    _order = 'date desc'



    def compute_info(self):
        ctx = self.env.context
        for one in self:
            partner = one.partner_id

            # payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='yjzy_payment_id.currency_id', readonly=True)
            # payment_currency_id = fields.Many2one('res.currency', u'收款货币', related='fk_journal_id.currency_id', readonly=True)
            if one.sfk_type == 'yfhxd':
                one.payment_currency_id = one.fk_journal_id.currency_id
            elif one.sfk_type == 'yshxd':
                one.payment_currency_id = one.yjzy_payment_id.currency_id
            else:
                one.payment_currency_id = one.yjzy_payment_id.currency_id

            if not one.payment_currency_id:
                one.payment_currency_id = one.manual_payment_currency_id


            if one.line_ids:
                invoices = one.line_ids.mapped('invoice_id')
                sale_orders = invoices.mapped('invoice_line_ids').mapped('sale_line_ids').mapped('order_id')
                #invoice_currency = one.invoice_ids[0].currency_id
                #<jon>
                invoice_currency = one.line_ids[0].invoice_currency_id

                company_currency = one.currency_id

                one.invoice_currency_id = invoice_currency
                one.amount_invoice_residual_org = sum([x.residual for x in invoices])
                one.amount_invoice = sum(
                    [invoice_currency.with_context(date=x.date_invoice).compute(x.residual, company_currency) for x in
                     invoices])
                one.amount_advance_residual_org = one.partner_type == 'customer' and sum(
                    [x.advance_residual for x in sale_orders]) \
                                                  or partner.advance_currency_id.compute(
                    partner.amount_purchase_advance_org, invoice_currency)
                one.amount_advance_residual = one.partner_type == 'customer' and invoice_currency.compute(
                    one.amount_advance_residual_org, company_currency) \
                                              or partner.advance_currency_id.compute(partner.amount_purchase_advance_org,
                                                                                     company_currency)

            if one.line_ids and one.payment_currency_id:
                date = one.date
                lines = one.line_ids
                if not one.line_ids:
                    continue
                bank_currency = one.payment_currency_id.with_context(date=date)
                diff_currency = one.payment_currency_id.with_context(date=date)
                payment_currency = one.payment_currency_id.with_context(date=date)

                one.amount_advance_org = sum([x.amount_advance_org for x in lines])
                one.amount_advance = sum([x.amount_advance for x in lines])
                one.amount_bank_org = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]), one.invoice_currency_id)
                one.amount_bank = sum([x.amount_bank for x in lines])
                one.amount_diff_org = diff_currency and diff_currency.compute(sum([x.amount_diff_org for x in lines]), one.invoice_currency_id)
                one.amount_diff = sum([x.amount_diff for x in lines])
                one.amount_payment_org = payment_currency and payment_currency.compute(sum([x.amount_payment_org for x in lines]),
                                                                  one.invoice_currency_id)
                one.amount_payment = sum([x.amount_payment for x in lines])
                one.amount_total_org = sum([x.amount_total_org for x in lines])
                one.amount_total = sum([x.amount_total for x in lines])
                one.amount_exchange = one.amount_invoice - one.amount_total

                one.other_feiyong_amount = one.amount_payment_org + one.feiyong_amount
                one.final_coat =  one.other_feiyong_amount - one.back_tax_amount

    def compute_by_invoice(self):
        for one in self:
            if not one.line_ids:
                continue

            invoices = one.line_ids.mapped('invoice_id')
            if len(one.invoice_ids.mapped('currency_id')) > 1:
                raise Warning('选择的发票的交易货币不一致')

            sale_orders = invoices.mapped('invoice_line_ids').mapped('sale_line_ids').mapped('order_id')
            #invoice_currency = one.invoice_ids[0].currency_id
            #<jon>
            invoice_currency = one.line_ids[0].invoice_currency_id


            company_currency = one.currency_id
            partner = one.partner_id

            one.invoice_currency_id = invoice_currency
            one.amount_invoice_residual_org = sum([x.residual for x in invoices])
            one.amount_invoice = sum(
                [invoice_currency.with_context(date=x.date_invoice).compute(x.residual, company_currency) for x in
                 invoices])
            one.amount_advance_residual_org = one.partner_type == 'customer' and sum(
                [x.advance_residual for x in sale_orders]) \
                                              or partner.advance_currency_id.compute(
                partner.amount_purchase_advance_org, invoice_currency)
            one.amount_advance_residual = one.partner_type == 'customer' and invoice_currency.compute(
                one.amount_advance_residual_org, company_currency) \
                                          or partner.advance_currency_id.compute(partner.amount_purchase_advance_org,
                                                                                 company_currency)

    def compute_by_lines(self):
        for one in self:
            date = one.date
            if (not one.line_ids) or (not one.payment_currency_id):
                continue
            bank_currency = one.payment_currency_id.with_context(date=date)
            diff_currency = one.payment_currency_id.with_context(date=date)
            payment_currency = one.payment_currency_id.with_context(date=date)

            lines = one.line_ids
            # lines.compute_info()

            one.amount_advance_org = sum([x.amount_advance_org for x in lines])
            one.amount_advance = sum([x.amount_advance for x in lines])
            one.amount_bank_org = bank_currency and bank_currency.compute(sum([x.amount_bank_org for x in lines]),
                                                        one.invoice_currency_id)
            one.amount_bank = sum([x.amount_bank for x in lines])
            one.amount_diff_org = diff_currency.compute(sum([x.amount_diff_org for x in lines]),
                                                        one.invoice_currency_id)
            one.amount_diff = sum([x.amount_diff for x in lines])
            one.amount_payment_org = payment_currency.compute(sum([x.amount_payment_org for x in lines]),
                                                              one.invoice_currency_id)
            one.amount_payment = sum([x.amount_payment for x in lines])
            one.amount_total_org = sum([x.amount_total_org for x in lines])
            one.amount_total = sum([x.amount_total for x in lines])
            one.amount_exchange = one.amount_invoice - one.amount_total

    def default_bank_currency(self):
        return self.env.user.company_id.currency_id

    def default_diff_currency(self):
        return self.env.user.company_id.currency_id.id

    def default_journal(self):
        domain = [('type', '=', 'misc')]
        sfk_type = self.env.context.get('default_sfk_type', '')
        domain = []
        if sfk_type == 'yfhxd':
            domain = [('code', '=', 'yfdrl'), ('company_id', '=', self.env.user.company_id.id)]
        if sfk_type == 'yshxd':
            domain = [('code', '=', 'ysdrl'), ('company_id', '=', self.env.user.company_id.id)]

        journal = self.env['account.journal'].search(domain, limit=1)
        return journal and journal.id

    def default_payment_account(self):
        account_obj = self.env['account.account']
        bank_account = account_obj.search([('code', '=', '10021'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
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



    name = fields.Char(u'编号', default=lambda self: self._default_name())
    payment_type = fields.Selection([('outbound', u'付款'), ('inbound', u'收款'), ('claim_in', u'收款认领'), ('claim_out', u'付款认领')], string=u'收/付款',
                                    required=True)
    partner_type = fields.Selection([('customer', u'客户'), ('supplier', u'供应商')], string=u'伙伴类型', )
    journal_id = fields.Many2one('account.journal', u'日记账', required=True, default=lambda self: self.default_journal())
    company_id = fields.Many2one('res.company', string=u'公司', required=True, default=lambda self: self.env.user.company_id)
    partner_id = fields.Many2one('res.partner', u'合作伙伴', required=True)
    currency_id = fields.Many2one(related='company_id.currency_id', string=u'公司货币', store=True, index=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', compute=compute_info)

    state = fields.Selection([('draft', u'草稿'), ('posted', u'提交'),  ('approved', u'批准'), ('done', u'完成'), ('cancelled', u'取消')],
                             readonly=True, default='draft', copy=False, string=u"状态")

    date = fields.Date(u'确认日期', index=True, required=True, default=lambda self: fields.date.today())
    invoice_ids = fields.One2many('account.invoice', 'reconcile_order_id', u'发票')
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

    payment_currency_id = fields.Many2one('res.currency', u'收款货币', compute=compute_info, readonly=True)
    manual_payment_currency_id = fields.Many2one('res.currency', u'收款货币:手动输入')


    manual_currency_id = fields.Many2one('res.currency', u'手动设置收款货币',)


    # 1银行扣款和销售费用的货币随收款货币；
    # bank_currency_id = fields.Many2one('res.currency', u'银行扣款货币', required=True,
    #                                    default=lambda self: self.default_bank_currency())
    # diff_currency_id = fields.Many2one('res.currency', u'销售费用货币', required=True,
    #                                    default=lambda self: self.default_diff_currency())

    amount_invoice_org = fields.Monetary(u'发票金额', currency_field='invoice_currency_id', compute=compute_by_invoice)

    amount_invoice_residual_org = fields.Monetary(u'发票余额', currency_field='invoice_currency_id', compute=compute_by_invoice)

    amount_advance_residual_org = fields.Monetary(u'待核销预收', currency_field='invoice_currency_id',
                                                  compute=compute_by_invoice)
    amount_advance_org = fields.Monetary(u'使用预收', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_diff_org = fields.Monetary(u'销售费用', currency_field='invoice_currency_id', compute=compute_by_lines)
    # amount_exchange_org = fields.Monetary(u'汇兑差异', currency_field='invoice_currency_id', compute=compute_by_lines)
    amount_total_org = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_by_lines, store=False)

    amount_invoice = fields.Monetary(u'发票金额', currency_field='currency_id', compute=compute_by_invoice)
    amount_advance_residual = fields.Monetary(u'待核销预收', currency_field='currency_id', compute=compute_by_invoice)
    amount_advance = fields.Monetary(u'使用预收', currency_field='currency_id', compute=compute_by_lines)
    amount_payment = fields.Monetary(u'收款金额', currency_field='currency_id', compute=compute_by_lines)
    amount_bank = fields.Monetary(u'银行扣款', currency_field='currency_id', compute=compute_by_lines)
    amount_diff = fields.Monetary(u'销售费用', currency_field='currency_id', compute=compute_by_lines)
    amount_exchange = fields.Monetary(u'汇兑差异', currency_field='currency_id', compute=compute_by_lines)
    amount_total = fields.Monetary(u'收款合计:本币', currency_field='currency_id', compute=compute_by_lines, store=False)

    line_ids = fields.One2many('account.reconcile.order.line', 'order_id', u'明细')
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

    other_feiyong_amount = fields.Monetary('其他费用金额', compute=compute_info)
    final_coat = fields.Monetary('最终成本', compute=compute_info)

    is_editable = fields.Boolean(u'可编辑')

    def unlink(self):
        for one in self:
            if one.state != 'cancelled':
                raise Warning(u'只有取消状态允许删除')
        return super(account_reconcile_order, self).unlink()


    def action_cancel(self):
        self.state = 'cancelled'

    def action_draft(self):
        self.state = 'draft'



    def action_approve(self):
        if self.fygb_id:
            fygb = self.fygb_id
            fygb.approve_expense_sheets()
        if self.back_tax_invoice_id:
            invoice = self.back_tax_invoice_id
            invoice.action_invoice_open()
        self.state = 'approved'

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
        })

        self.yjzy_payment_id = payment


    @api.onchange('journal_id')
    def onchange_journal(self):
        self.payment_account_id = self.journal_id.default_debit_account_id

    @api.onchange('partner_type')
    def _onchange_partner_type(self):
        if self.partner_type:
            return {'domain': {'partner_id': [(self.partner_type, '=', True)]}}

    def action_posted(self):
        self.ensure_one()
        self.state = 'posted'
        #self.date = fields.date.today()
        return True

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



    @api.onchange('partner_id')
    def onchange_partner(self):
        if self.partner_id:
            self.invoice_ids.write({'reconcile_order_id': None})
            self.line_ids = False

    def check_amount(self):
        self.ensure_one()

    def _prepare_account_move(self):
        return {
            'name': self.journal_id.with_context(ir_sequence_date=self.date).sequence_id.next_by_id(),
            'date': self.date,
            'ref': self.name,
            'company_id': self.company_id.id,
            'journal_id': self.journal_id.id,
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
            'new_payment_id': self.yjzy_payment_id.id,
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

    def _prepare_sale_invoice_line(self, inv):
        self.ensure_one()
        dic_so_invl = {}
        for line in inv.invoice_line_ids:
            if line.sale_line_ids:
                so = line.sale_line_ids[0].order_id
                if so in dic_so_invl:
                    dic_so_invl[so] |= line
                else:
                    dic_so_invl[so] = line
        return dic_so_invl

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
        return dic_po_invl

    def make_lines(self):
        self.ensure_one()
        if self.partner_type == 'customer':
            self._make_lines_so()
        if self.partner_type == 'supplier':
            self._make_lines_po()

    def _make_lines_po(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        self.line_ids = None

        if self.no_sopo:
            for invoice in self.invoice_ids:
                line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
        else:
            for invoice in self.invoice_ids:
                po_invlines = self._prepare_purchase_invoice_line(invoice)
                for po, invlines in po_invlines.items():
                    line_obj.create({
                        'order_id': self.id,
                        'po_id': po.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })

    def _make_lines_so(self):
        self.ensure_one()
        line_obj = self.env['account.reconcile.order.line']
        self.line_ids = None
        if self.no_sopo:
            for invoice in self.invoice_ids:
                line_obj.create({
                    'order_id': self.id,
                    'invoice_id': invoice.id,
                    'amount_invoice_so': invoice.amount_total,
                })
        else:
            for invoice in self.invoice_ids:
                so_invlines = self._prepare_sale_invoice_line(invoice)
                for so, invlines in so_invlines.items():
                    line_obj.create({
                        'order_id': self.id,
                        'so_id': so.id,
                        'invoice_id': invoice.id,
                        'amount_invoice_so': sum([i.price_subtotal for i in invlines]),
                    })

    def clear_moves(self):
        self.ensure_one()
        self.move_ids.write({'reconcile_order_id': False})

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
        self.state = 'done'
        return True


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
            # one.amount_exchange = invoice_currency.compute(one.amount_exchange_org, company_currency)
            ###
            amount_total_org = one.amount_advance_org
            if payment_currency and invoice_currency:
                amount_total_org += payment_currency.compute(one.amount_payment_org, invoice_currency)
            if bank_currency and invoice_currency:
                amount_total_org += bank_currency.compute(one.amount_bank_org, invoice_currency)
            if diff_currency and invoice_currency:
                amount_total_org += diff_currency.compute(one.amount_diff_org, invoice_currency)

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

    # @api.onchange('amount_invoice_so', 'amount_advance_org', 'amount_bank_org', 'amount_diff_org', 'amount_payment_org')
    # def onchange_amount(self):
    #     self.amount_exchange_org = self.amount_invoice_so - self.amount_advance_org - self.amount_bank_org - self.amount_diff_org - self.amount_payment_org

    order_id = fields.Many2one('account.reconcile.order', u'核销单')
    partner_type = fields.Selection(related='order_id.partner_type')
    payment_type = fields.Selection(related='order_id.payment_type')

    so_id = fields.Many2one('sale.order', u'销售单')
    so_contract_code = fields.Char(u'销售合同号', related='so_id.contract_code', readonly=True)




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

    advance_residual = fields.Monetary(currency_field='yjzy_currency_id', string=u'预付余额', compute=compute_info, )
    advance_residual2 = fields.Monetary(currency_field='yjzy_currency_id', string=u'预收余额', compute=compute_info, )

    advance_account_id = fields.Many2one(related='so_id.advance_account_id', string='预收账户')

    yjzy_payment_id = fields.Many2one('account.payment', u'预收认领单', related='so_id.yjzy_payment_id')
    yjzy_currency_id = fields.Many2one('res.currency', u'预收币种', related='yjzy_payment_id.currency_id')
    amount_advance_org = fields.Monetary(u'预收金额', currency_field='yjzy_currency_id')

    amount_advance = fields.Monetary(u'预收金额:本币', currency_field='currency_id', compute=compute_info)
    amount_payment_org = fields.Monetary(u'收款金额', currency_field='payment_currency_id')
    amount_payment = fields.Monetary(u'收款金额:本币', currency_field='currency_id', compute=compute_info)
    amount_bank_org = fields.Monetary(u'银行扣款', currency_field='payment_currency_id')
    amount_bank = fields.Monetary(u'银行扣款:本币', currency_field='currency_id', compute=compute_info)
    amount_diff_org = fields.Monetary(u'销售费用', currency_field='payment_currency_id')
    amount_diff = fields.Monetary(u'销售费用:本币', currency_field='currency_id', compute=compute_info)
    amount_exchange_org = fields.Monetary(u'汇兑差异', currency_field='invoice_currency_id')
    amount_exchange = fields.Monetary(u'汇兑差异:本币', currency_field='currency_id')
    amount_total_org = fields.Monetary(u'收款合计', currency_field='invoice_currency_id', compute=compute_info)
    amount_total = fields.Monetary(u'收款合计:本币', currency_field='currency_id', compute=compute_info)
