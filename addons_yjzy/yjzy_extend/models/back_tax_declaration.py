# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree
from datetime import datetime, timedelta
from .comm import invoice_attribute_all_in_one

class DeclareDeclaration(models.Model):
    _name = 'back.tax.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '报关申报表'
    _order = 'id desc'


    @api.depends('btd_line_ids','btd_line_ids.invoice_amount_total')
    def compute_invoice_amount_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            invoice_amount_all = sum(x.invoice_amount_total for x in btd_line_ids)
            one.invoice_amount_all = invoice_amount_all

    @api.depends('btd_line_ids', 'btd_line_ids.invoice_residual_total')
    def compute_invoice_residual_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            invoice_residual_all = sum(x.invoice_residual_total for x in btd_line_ids)
            one.invoice_residual_all = invoice_residual_all

    @api.depends('btd_line_ids', 'btd_line_ids.declaration_amount')
    def compute_declaration_amount(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            declaration_amount_all = sum(x.declaration_amount for x in btd_line_ids)
            one.declaration_amount_all = declaration_amount_all


    @api.depends('reconcile_order_ids','reconcile_order_ids.amount_total_org_new')
    def compute_reconcile_amount(self):
        for one in self:
            reconcile_amount = sum(x.amount_total_org_new for x in one.reconcile_order_ids)
            declaration_amount_all = one.declaration_amount_all
            one.reconcile_amount = reconcile_amount
            one.declaration_amount_all_residual = declaration_amount_all - reconcile_amount

    @api.depends('btd_line_ids','btd_line_ids.declaration_amount_residual')
    def compute_declaration_amount_all_residual_new(self):
        for one in self:
            declaration_amount_all_residual_new = sum(x.declaration_amount_residual for x in one.btd_line_ids)
            one.declaration_amount_all_residual_new = declaration_amount_all_residual_new

    def compute_display_name(self):
        for one in self:
            name = '%s:%s' % ('退税申报',one.name)
            one.display_name = name


    @api.depends('btd_line_ids')
    def compute_invoice_ids(self):
        tb_contract_code = ''
        for one in self:
            invoice_ids = one.btd_line_ids.mapped('invoice_id')
            for x in invoice_ids:
                tb_contract_code += '%s,' % (x.tb_contract_code)
            one.invoice_ids = invoice_ids
            one.tb_contract_code = tb_contract_code

    @api.depends('declaration_amount_all','invoice_amount_all')
    def compute_diff_tax_amount(self):
        for one in self:
            one.diff_tax_amount = one.declaration_amount_all - one.invoice_amount_all

    payment_id = fields.Many2one('account.payment','收款单')
    payment_amount = fields.Monetary('收款金额',currency_field='company_currency_id',related='payment_id.amount')
    payment_balance = fields.Monetary('未认领金额',currency_field='company_currency_id',related='payment_id.balance')
    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('back.tax.declaration'))
    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    btd_line_ids = fields.One2many('back.tax.declaration.line','btd_id',u'申报明细')
    invoice_ids = fields.Many2many('account.invoice',compute=compute_invoice_ids,store=True)
    tb_contract_code = fields.Char('合同号',compute=compute_invoice_ids,store=True)
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    state = fields.Selection([('draft',u'草稿'),('done',u'确认'),('paid',u'已收款'),('cancel',u'取消')],'State', default='draft')
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    declaration_title = fields.Char('申报说明')
    declaration_date = fields.Date('申报日期')
    invoice_amount_all = fields.Monetary(u'原始应收退税',currency_field='company_currency_id',compute=compute_invoice_amount_all, store=True)
    invoice_residual_all = fields.Monetary(u'剩余应收退税',currency_field='company_currency_id',compute=compute_invoice_residual_all,store=True)
    declaration_amount_all = fields.Monetary(u'本次申报金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)
    declaration_amount_all_residual_new = fields.Monetary(u'申报剩余金额', currency_field='company_currency_id',
                                             compute=compute_declaration_amount_all_residual_new, store=True)
    company_id = fields.Many2one('res.company', string='Company',required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    reconcile_order_ids = fields.One2many('account.reconcile.order','back_tax_declaration_id','核销单')
    reconcile_amount = fields.Monetary('收款认领金额',currency_field='company_currency_id',compute=compute_reconcile_amount,store=True)
    declaration_amount_all_residual = fields.Monetary(u'本次申报金额收款金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)

    diff_tax_amount = fields.Monetary('申报和应收差额',currency_field='company_currency_id',compute=compute_diff_tax_amount,store=True)

    def create_other_invoice(self):
        diff_tax_amount = self.diff_tax_amount
        invoice_obj = self.env['account.invoice']
        btd_line = self.env['back.tax.declaration.line']
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        product = self.env.ref('yjzy_extend.product_back_tax')
        # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
        account = product.property_account_income_id


        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        if len(self.btd_line_ids.filtered(lambda x: x.invoice_attribute_all_in_one == '630')) > 0:
            raise Warning(u'已经存在调节账单')
        else:
            if diff_tax_amount > 0:
                back_tax_invoice = invoice_obj.create({
                    'partner_id': partner.id,
                    'type': 'out_invoice',
                    'journal_type': 'sale',
                    'date_invoice': datetime.today(),
                    'date': datetime.today(),
                    'yjzy_type': 'back_tax',
                    'yjzy_type_1': 'back_tax',
                    'invoice_attribute': 'extra',
                    'invoice_type_main': '20_extra',
                    # 'invoice_attribute_all_in_one':'630',
                    'back_tax_declaration_id':self.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '007')], limit=1).id,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': self.diff_tax_amount,
                        'account_id': account.id,
                    })]
                })
                # 730 创建后直接过账
                # back_tax_invoice.yjzy_invoice_id = back_tax_invoice.id

                back_tax_invoice.action_invoice_open()
                btd_line_id=btd_line.create({
                    'invoice_id':back_tax_invoice.id,
                    'declaration_amount':0,
                    'btd_id':self.id
                })
            elif diff_tax_amount == 0:
                return True
            else:
                back_tax_invoice = invoice_obj.create({
                    'partner_id': partner.id,
                    'type': 'out_refund',
                    'journal_type': 'sale',
                    'date_invoice': datetime.today(),
                    'date': datetime.today(),
                    'yjzy_type': 'back_tax',
                    'yjzy_type_1': 'back_tax',
                    'invoice_attribute': 'extra',
                    'invoice_type_main': '20_extra',
                    # 'invoice_attribute_all_in_one':'630',
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '007')], limit=1).id,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': -diff_tax_amount,
                        'account_id': account.id,
                    })]
                })
                # 730 创建后直接过账
                # back_tax_invoice.yjzy_invoice_id = back_tax_invoice.id

                back_tax_invoice.action_invoice_open()
                btd_line_id = btd_line.create({
                    'invoice_id': back_tax_invoice.id,
                    'declaration_amount': 0,
                    'btd_id': self.id
                })
                move_obj = self.env['account.move.line']
                #将需要核销的发票和新增的退税退款发票关联起来，
                for inv_line in self.btd_line_ids:
                    if inv_line.invoice_attribute_all_in_one != '630':
                        move_line = inv_line.invoice_id.move_line_ids.filtered(lambda x:x.invoice_id == inv_line.invoice_id
                        and x.reconciled == False and x.account_id.code == '1122')
                        move_line.plan_invoice_id = back_tax_invoice#这个是和调节退税关联
                        print('move_line_akiny', move_line,back_tax_invoice.number)
                        # back_tax_invoice.assign_outstanding_credit(move_line.id)
                print('self_akiny',btd_line_id,back_tax_invoice)



    @api.multi
    def name_get(self):
        res = []
        for one in self:
            name = '%s:%s' % (one.name, one.declaration_amount_all)
            res.append((one.id, name))
        return res

    def unlink(self):
        for one in self:
            if one.state not in ['draft', 'cancel']:
                raise Warning(u'不能删除非草稿成本单据')
        return super(DeclareDeclaration, self).unlink()

    def action_confirm(self):


        if len(self.btd_line_ids.filtered(lambda x: x.invoice_back_tax_declaration_state == '20')) > 0:
            raise Warning('明细行存在已经申报的应收退税账单，请查验!')
        for one in self.btd_line_ids:
            if one.declaration_amount == 0 and one.invoice_attribute_all_in_one != '630':
                raise Warning('申报金额不允许为0')
            # if one.declaration_amount > one.invoice_residual_total:
            #     raise Warning('申报金额不允许大于未收退税金额！')
        if not self.declaration_date:
            return Warning('请填写申报日期')
        self.state = 'done'
        invoice_ids = self.btd_line_ids.mapped('invoice_id')
        for one in invoice_ids:
            one.back_tax_declaration_state = '20'


    def action_cancel(self):
        invoice_paid_lines = self.btd_line_ids.filtered(lambda x:x.invoice_id.state == 'paid' and x.invoice_id.yjzy_type == 'back_tax')
        if len(invoice_paid_lines) !=0:
            raise Warning('已经收款认领，不允许取消申报单！')
        else:
            self.state = 'draft'
            line_ids = self.btd_line_ids.mapped('invoice_id')
            for one in line_ids:
                one.back_tax_declaration_state = '10'



    def open_wizard_back_tax_declaration(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        ctx.update({
            'default_gongsi_id': self.gongsi_id.id,
            # 'default_have_invoice_ids':self.btd_line_ids.ids#[(6, 0, self.btd_line_ids.ids)],

        })
        return {
            'name': '添加应收退税账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.back.tax.declaration',
            'target': 'new',
            'type': 'ir.actions.act_window',

            'context': ctx,
        }


    def test_reconcile(self):
        line_id = self.btd_line_ids.filtered(lambda x:x.invoice_attribute_all_in_one == '630')
        for one in self.btd_line_ids:
            if one.invoice_attribute_all_in_one != '630' and one.diff_tax < 0:
                one.yjzy_invoice_id = line_id



class DeclareDeclarationLine(models.Model):
    _name = 'back.tax.declaration.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '退税申报明细'
    _order = 'id desc'

    @api.depends('invoice_id','invoice_id.amount_total')
    def compute_invoice_amount_total(self):
        for one in self:
            one.invoice_amount_total = one.invoice_id.amount_total_signed


    @api.depends('invoice_id', 'invoice_id.residual')
    def compute_invoice_residual(self):
        for one in self:
            one.invoice_residual_total = one.invoice_id.residual_signed

    @api.depends('declaration_amount','invoice_residual_total','declaration_amount')
    def compute_declaration_amount_residual(self):
        for one in self:
            declaration_amount_residual = one.declaration_amount - (one.invoice_amount_total - one.invoice_residual_total)
            one.declaration_amount_residual = declaration_amount_residual

    @api.depends('declaration_amount', 'invoice_amount_total')
    def compute_diff_tax(self):
        for one in self:
            diff_tax = one.declaration_amount - one.invoice_amount_total
            one.diff_tax = diff_tax

    btd_id = fields.Many2one('back.tax.declaration',u'退税申报单',ondelete='cascade',  required=True)
    invoice_id = fields.Many2one('account.invoice',u'账单', required=True)
    invoice_back_tax_declaration_state = fields.Selection([('10','未申报'),('20','已申报')],'退税申报状态',related='invoice_id.back_tax_declaration_state')
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    invoice_amount_total = fields.Monetary(u'账单原始金额',currency_field='invoice_currency_id',compute=compute_invoice_amount_total,store=True)
    invoice_residual_total = fields.Monetary(u'账单剩余金额',currency_field='invoice_currency_id',compute=compute_invoice_residual,store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='btd_id.company_id', store=True, readonly=True, related_sudo=False)
    declaration_amount = fields.Monetary(u'退税申报金额',currency_field='invoice_currency_id')
    diff_tax = fields.Monetary(u'申报和原始应收差额',currency_field='invoice_currency_id',compute='compute_diff_tax',store=True)
    declaration_amount_residual = fields.Monetary(u'未收款申报金额',currency_field='invoice_currency_id',compute=compute_declaration_amount_residual,store=True)
    comments = fields.Text(u'备注')
    invoice_attribute_all_in_one = fields.Selection(invoice_attribute_all_in_one, u'账单属性all_in_one',
                                                    related='invoice_id.invoice_attribute_all_in_one', store=True)













#####################################################################################################################
