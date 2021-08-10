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


    @api.depends('btd_line_ids','btd_line_ids.invoice_amount_total','btd_line_ids.invoice_attribute_all_in_one')
    def compute_invoice_amount_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            btd_line_630_ids = one.btd_line_ids.filtered(lambda x: x.back_tax_type == 'adjustment')
            btd_line_no_630_ids = one.btd_line_ids.filtered(lambda x: x.back_tax_type != 'adjustment')
            invoice_amount_all = sum(x.invoice_amount_total for x in btd_line_ids)
            invoice_amount_630 = sum(x.invoice_amount_total for x in btd_line_630_ids)
            invoice_amount_no_630 = sum(x.invoice_amount_total for x in btd_line_no_630_ids)
            one.invoice_amount_all = invoice_amount_all
            one.invoice_amount_630 = invoice_amount_630
            one.invoice_amount_no_630 = invoice_amount_no_630

    @api.depends('btd_line_ids', 'btd_line_ids.invoice_residual_total','btd_line_ids.invoice_attribute_all_in_one')
    def compute_invoice_residual_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            btd_line_630_ids = one.btd_line_ids.filtered(lambda x: x.back_tax_type == 'adjustment')
            btd_line_no_630_ids = one.btd_line_ids.filtered(lambda x: x.back_tax_type != 'adjustment')
            invoice_residual_all = sum(x.invoice_residual_total for x in btd_line_ids)
            invoice_residual_630 = sum(x.invoice_residual_total for x in btd_line_630_ids)
            invoice_residual_no_630 = sum(x.invoice_residual_total for x in btd_line_no_630_ids)
            one.invoice_residual_all = invoice_residual_all
            one.invoice_residual_630 = invoice_residual_630
            one.invoice_residual_no_630 = invoice_residual_no_630


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
    btd_line_ids = fields.One2many('back.tax.declaration.line','btd_id',u'申报明细'
                                   )#domain=['|','&',('back_tax_type','!=','adjustment'),('back_tax_type','=','adjustment'),('invoice_residual_total','!=',0)]

    invoice_ids = fields.Many2many('account.invoice',compute=compute_invoice_ids,store=True)
    tb_contract_code = fields.Char('合同号',compute=compute_invoice_ids,store=True)
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    state = fields.Selection([('draft',u'草稿'),('approval','审批中'),('done',u'确认'),('paid',u'已收款'),('cancel',u'取消')],'State', default='draft')
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    declaration_title = fields.Char('申报说明')
    declaration_date = fields.Date('申报日期')
    invoice_amount_all = fields.Monetary(u'调节后应收退税',currency_field='company_currency_id',compute=compute_invoice_amount_all, store=True)
    invoice_amount_630 = fields.Monetary(u'调节应收退税',currency_field='company_currency_id',compute=compute_invoice_amount_all, store=True)
    invoice_amount_no_630 = fields.Monetary(u'调节前应收退税', currency_field='company_currency_id',
                                         compute=compute_invoice_amount_all, store=True)

    invoice_residual_all = fields.Monetary(u'调节后剩余退税',currency_field='company_currency_id',compute=compute_invoice_residual_all,store=True)
    invoice_residual_630 = fields.Monetary(u'剩余调节退税', currency_field='company_currency_id',
                                           compute=compute_invoice_residual_all, store=True)
    invoice_residual_no_630 = fields.Monetary(u'原始剩余退税', currency_field='company_currency_id',
                                           compute=compute_invoice_residual_all, store=True)
    declaration_amount_all = fields.Monetary(u'本次申报金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)
    declaration_amount_all_residual_new = fields.Monetary(u'申报剩余金额', currency_field='company_currency_id',
                                             compute=compute_declaration_amount_all_residual_new, store=True)
    company_id = fields.Many2one('res.company', string='Company',required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    reconcile_order_ids = fields.One2many('account.reconcile.order','back_tax_declaration_id','核销单')
    reconcile_amount = fields.Monetary('收款认领金额',currency_field='company_currency_id',compute=compute_reconcile_amount,store=True)
    declaration_amount_all_residual = fields.Monetary(u'本次申报金额收款金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)

    diff_tax_amount = fields.Monetary('申报和应收差额',currency_field='company_currency_id',compute=compute_diff_tax_amount,store=True)
    tuishuirld_id = fields.Many2one('account.payment',u'退税申报认领单')
    back_tax_all_in_one_invoice_id = fields.Many2one('account.invoice',u'退税申报账单')

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


    #创建调节账单这个有大于的时候的计算，目前不做计算
    def ____create_adjustment_invoice(self):

        diff_tax_amount = self.diff_tax_amount
        invoice_obj = self.env['account.invoice']
        btd_line = self.env['back.tax.declaration.line']
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        product = self.env.ref('yjzy_extend.product_back_tax')
        # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
        account = product.property_account_income_id


        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        print('btd_line_ids_akiny',self.btd_line_ids)
        for line in self.btd_line_ids:
            invoice_attribute = line.invoice_id.invoice_attribute
            if line.diff_tax > 0:
                back_tax_invoice = invoice_obj.create({
                    'partner_id': partner.id,
                    'type': 'out_invoice',
                    'journal_type': 'sale',
                    'date_invoice': datetime.today(),
                    'date': datetime.today(),
                    'yjzy_type': 'back_tax',
                    'yjzy_type_1': 'back_tax',
                    'invoice_attribute': invoice_attribute,
                    'invoice_type_main': '20_extra',
                    # 'invoice_attribute_all_in_one':invoice_attribute_all_in_one,
                    'back_tax_type':'adjustment',
                    'back_tax_declaration_id': self.id,
                    'yjzy_invoice_id':line.invoice_id.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '007')], limit=1).id,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': line.diff_tax,
                        'account_id': account.id,
                    })]
                })

                back_tax_invoice.action_invoice_open()
                # back_tax_invoice.invoice_assign_outstanding_credit()
                line.invoice_id.adjustment_invoice_id = back_tax_invoice
                year = fields.datetime.now().strftime('%Y')
                number = int(line.line_name[4:]) + 1

                if len(str(number)) ==1:
                    number_str = '0000000'
                elif len(str(number)) ==2:
                    number_str = '000000'
                elif len(str(number)) ==3:
                    number_str = '00000'
                elif len(str(number)) ==4:
                    number_str = '0000'
                elif len(str(number)) ==5:
                    number_str = '000'
                elif len(str(number)) ==6:
                    number_str = '00'
                elif len(str(number)) ==7:
                    number_str = '0'
                else:
                    number_str = ''

                line_name_new='%s%s%s' % (year,number_str,int(line.line_name[4:])+1)
                print('line_name_new_akiny',line_name_new)
                declaration_amount = line.declaration_amount
                diff_tax = line.diff_tax
                declaration_amount_new = declaration_amount - diff_tax
                line.declaration_amount = declaration_amount_new
                btd_line_id = btd_line.create({
                    'line_name':line_name_new,
                    'invoice_id': back_tax_invoice.id,
                    'declaration_amount': diff_tax,
                    'btd_id': self.id
                })
            elif line.diff_tax == 0:
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
                    'invoice_attribute': invoice_attribute,
                    'invoice_type_main': '20_extra',
                    # 'invoice_attribute_all_in_one':invoice_attribute_all_in_one,
                    'back_tax_type': 'adjustment',
                    'back_tax_declaration_id': self.id,
                    'yjzy_invoice_id': line.invoice_id.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '007')], limit=1).id,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': -line.diff_tax,
                        'account_id': account.id,
                    })]
                })
                back_tax_invoice.action_invoice_open()
                back_tax_invoice.invoice_assign_outstanding_credit()
                line.invoice_id.adjustment_invoice_id = back_tax_invoice
                year = fields.datetime.now().strftime('%Y')
                number = int(line.line_name[4:]) + 1
                if len(str(number)) == 1:
                    number_str = '0000000'
                elif len(str(number)) == 2:
                    number_str = '000000'
                elif len(str(number)) == 3:
                    number_str = '00000'
                elif len(str(number)) == 4:
                    number_str = '0000'
                elif len(str(number)) == 5:
                    number_str = '000'
                elif len(str(number)) == 6:
                    number_str = '00'
                elif len(str(number)) == 7:
                    number_str = '0'
                else:
                    number_str = ''
                line_name_new = '%s%s%s' % (year, number_str, int(line.line_name[4:]) + 1)
                print('line_name_new_akiny', line_name_new)


                btd_line_id = btd_line.create({
                    'line_name': line_name_new,
                    'invoice_id': back_tax_invoice.id,
                    'declaration_amount': 0,
                    'btd_id': self.id
                })

    # 创建调节账单
    def create_adjustment_invoice(self):
        diff_tax_amount = self.diff_tax_amount
        invoice_obj = self.env['account.invoice']
        btd_line = self.env['back.tax.declaration.line']
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        product = self.env.ref('yjzy_extend.product_back_tax')
        # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
        account = product.property_account_income_id
        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        print('btd_line_ids_akiny', self.btd_line_ids)
        # for line_1 in self.btd_line_ids:
        #     if line_1.diff_tax > 0:
        #         raise Warning(u'申报退税金额不允许大于系统应收退税金额！')
        for line in self.btd_line_ids:
            invoice_attribute = line.invoice_id.invoice_attribute
            if line.diff_tax > 0:
                raise Warning(u'申报退税金额不允许大于系统应收退税金额！')
            elif line.diff_tax < 0:
                back_tax_invoice = invoice_obj.create({
                    'partner_id': partner.id,
                    'type': 'out_refund',
                    'journal_type': 'sale',
                    'date_invoice': datetime.today(),
                    'date': datetime.today(),
                    'yjzy_type': 'back_tax',
                    'yjzy_type_1': 'back_tax',
                    'invoice_attribute': invoice_attribute,
                    'invoice_type_main': '20_extra',
                    # 'invoice_attribute_all_in_one':invoice_attribute_all_in_one,
                    'back_tax_type': 'adjustment',
                    'back_tax_declaration_id': self.id,
                    'yjzy_invoice_id': line.invoice_id.id,
                    'stage_id': self.env['account.invoice.stage'].search([('code', '=', '007')], limit=1).id,
                    'invoice_line_ids': [(0, 0, {
                        'name': '%s:%s' % (product.name, self.name),
                        'product_id': product.id,
                        'quantity': 1,
                        'price_unit': -line.diff_tax,
                        'account_id': account.id,
                    })]
                })
                line.invoice_id.is_adjustment = True
                back_tax_invoice.action_invoice_open()
                back_tax_invoice.invoice_assign_outstanding_credit()
                line.invoice_id.adjustment_invoice_id = back_tax_invoice
                year = fields.datetime.now().strftime('%Y')
                number = int(line.line_name[4:]) + 1
                if len(str(number)) == 1:
                    number_str = '0000000'
                elif len(str(number)) == 2:
                    number_str = '000000'
                elif len(str(number)) == 3:
                    number_str = '00000'
                elif len(str(number)) == 4:
                    number_str = '0000'
                elif len(str(number)) == 5:
                    number_str = '000'
                elif len(str(number)) == 6:
                    number_str = '00'
                elif len(str(number)) == 7:
                    number_str = '0'
                else:
                    number_str = ''
                line_name_new = '%s%s%s' % (year, number_str, int(line.line_name[4:]) + 1)
                print('line_name_new_akiny', line_name_new)

                btd_line_id = btd_line.create({
                    'line_name': line_name_new,
                    'invoice_id': back_tax_invoice.id,
                    'declaration_amount': 0,
                    'btd_id': self.id
                })
            else:
                continue





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

    def action_submit(self):
        if len(self.btd_line_ids.filtered(lambda x: x.invoice_back_tax_declaration_state == '20')) > 0:
            raise Warning('明细行存在已经申报的应收退税账单，请查验!')
        for one in self.btd_line_ids:
            if one.declaration_amount == 0 and one.invoice_attribute_all_in_one != '630':
                raise Warning('申报金额不允许为0')
            # if one.declaration_amount > one.invoice_residual_total:
            #     raise Warning('申报金额不允许大于未收退税金额！')
        if not self.declaration_date:
            raise Warning('请填写申报日期')
        self.create_adjustment_invoice()
        for one in self.btd_line_ids:
            one.invoice_id.back_tax_declaration_state = '20'
        self.state = 'approval'
        self.create_tuishuirld()

    def action_confirm(self):
        # if len(self.btd_line_ids.filtered(lambda x: x.invoice_back_tax_declaration_state == '20')) > 0:
        #     raise Warning('明细行存在已经申报的应收退税账单，请查验!')
        # for one in self.btd_line_ids:
        #     if one.declaration_amount == 0 and one.invoice_attribute_all_in_one != '630':
        #         raise Warning('申报金额不允许为0')
        #     # if one.declaration_amount > one.invoice_residual_total:
        #     #     raise Warning('申报金额不允许大于未收退税金额！')
        # if not self.declaration_date:
        #     return Warning('请填写申报日期')
        self.state = 'done'

        #0809 不再根据金额去判断部分申报，也就是不存在部分申报的概念了
        # for one in self.btd_line_ids:
        #     if one.invoice_id.declaration_amount == 0 :
        #         one.invoice_id.back_tax_declaration_state = '10'
        #     elif one.invoice_id.declaration_amount == one.invoice_amount_total:
        #         one.invoice_id.back_tax_declaration_state = '20'
        #     else:
        #         one.invoice_id.back_tax_declaration_state = '15'
        # invoice_ids = self.btd_line_ids.mapped('invoice_id')
        # for one in invoice_ids:
        #     if one.declaration_amount == 0:
        #         one.back_tax_declaration_state = '20'
        #     else:
        #         one.back_tax_declaration_state = '15'




    def action_refuse(self,reason):
        invoice_paid_lines = self.btd_line_ids.filtered(lambda x:x.invoice_id.state == 'paid' and x.invoice_id.yjzy_type == 'back_tax')
        if len(invoice_paid_lines) !=0:
            raise Warning('已经收款认领，不允许取消申报单！')
        else:
            self.state = 'draft'
            line_ids = self.btd_line_ids.mapped('invoice_id')
            for one in line_ids:
                one.back_tax_declaration_state = '10'
            for tb in self:
                tb.message_post_with_view('yjzy_extend.back_tax_template_refuse_reason',
                                          values={'reason': reason, 'name': self.declaration_title},
                                          subtype_id=self.env.ref(
                                              'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式



    def open_wizard_back_tax_declaration(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        ctx.update({
            'default_gongsi_id': self.gongsi_id.id,
            'default_have_invoice_ids':self.btd_line_ids.mapped('invoice_id').ids#[(6, 0, self.btd_line_ids.ids)],

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

    #创建一张付款单，把所有的退税账单都加入，待收款的时候完成统一过账
    def create_tuishuirld(self):
        self.ensure_one()
        invoice_dic = []
        line_ids = self.btd_line_ids.filtered(lambda x: x.invoice_residual_total >0)
        for one in line_ids:
            invoice_dic.append(one.invoice_id.id)
        print('invoice_dic', invoice_dic)

        sfk_type = 'tuishuirld'
        name = self.env['ir.sequence'].next_by_code('sfk.type.%s' % sfk_type)
        account_payment_obj = self.env['account.payment']
        partner_id = self.env.ref('yjzy_extend.partner_back_tax')

        journal_domain_tssb = [('code', '=', 'tssb'), ('company_id', '=', self.env.user.company_id.id)]
        journal_id_tssb = self.env['account.journal'].search(journal_domain_tssb, limit=1)
        reconcile_tuishui_id = account_payment_obj.create({
            'back_tax_declaration_id': self.id,
            'name': name,
            'sfk_type': sfk_type,
            'partner_id': partner_id.id,
            'amount': self.declaration_amount_all,
            'currency_id': self.company_currency_id.id,
            'payment_type': 'inbound',
            'partner_type': 'customer',
            'advance_ok': False,
            'journal_id': journal_id_tssb.id,
            'payment_method_id': 2,
            'invoice_ids': [(6, 0, invoice_dic)],
            'reconcile_type': '45_declaration_tax',
            'post_date': fields.date.today(),
        })

        self.tuishuirld_id = reconcile_tuishui_id
        for one in self.btd_line_ids:
            one.tuishuirld_id = reconcile_tuishui_id

    #方案一定稿
    def create_out_fund_invoice(self):
        self.ensure_one()
        invoice_obj = self.env['account.invoice']
        btd_line = self.env['back.tax.declaration.line']
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        product = self.env.ref('yjzy_extend.product_back_tax')
        account = product.property_account_income_id
        out_refund_invoice = invoice_obj.create({
            'partner_id': partner.id,
            'type': 'out_refund',
            'journal_type': 'sale',
            'date_invoice': datetime.today(),
            'date': datetime.today(),
            'yjzy_type': 'back_tax',
            'yjzy_type_1': 'back_tax',
            'invoice_attribute': 'extra',
            'invoice_type_main': '20_extra',
            # 'invoice_attribute_all_in_one':invoice_attribute_all_in_one,
            'df_all_in_one_invoice_id': self.id,
            'back_tax_type': 'adjustment',
            'back_tax_declaration_id': self.id,
            #'yjzy_invoice_id': line.invoice_id.id,
            'stage_id': self.env['account.invoice.stage'].search([('code', '=', '004')], limit=1).id,
            'invoice_line_ids': [(0, 0, {
                'name': '%s:%s' % (product.name, self.name),
                'product_id': product.id,
                'quantity': 1,
                'price_unit': self.invoice_residual_all,
                'account_id': account.id,
            })]
        })
        # create_back_tax_all_in_one_invoice
        invoice_tenyale_name = 'tenyale_invoice'
        tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % invoice_tenyale_name)
        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        back_tax_all_in_one_invoice = invoice_obj.create({
            'tenyale_name': tenyale_name,
            'partner_id': partner.id,
            'type': 'out_invoice',
            'journal_type': 'sale',
            'date_invoice': datetime.today(),
            'date': datetime.today(),
            'yjzy_type': 'back_tax',
            'yjzy_type_1': 'back_tax',
            # 'payment_term_id': payment_term_id.id,
            'invoice_attribute': 'extra',
            'invoice_type_main': '10_main',
            'df_all_in_one_invoice_id':self.id,
            # 'gongsi_id': self.purchase_gongsi_id.id,
            'stage_id': self.env['account.invoice.stage'].search([('code', '=', '004')], limit=1).id,

            'invoice_line_ids': [(0, 0, {
                'name': '%s:%s' % (product.name, self.name),
                'product_id': product.id,
                'quantity': 1,
                'price_unit': self.invoice_residual_all,
                'account_id': account.id,
            })]
        })
        self.back_tax_all_in_one_invoice_id = back_tax_all_in_one_invoice
        back_tax_all_in_one_invoice.back_tax_declaration_out_refund_invoice_id = out_refund_invoice

        out_refund_invoice.action_invoice_open()
        # line_ids = self.btd_line_ids.filtered(lambda x: x.invoice_residual_total > 0)
        for one in self.btd_line_ids:
            one.back_tax_all_in_one_invoice = back_tax_all_in_one_invoice
            one.invoice_id.yjzy_invoice_id = out_refund_invoice
            one.invoice_id.back_tax_assign_outstanding_credit()


            # 730 创建后直接过账






    def open_tuishuirld_id(self):
        form_view = self.env.ref('yjzy_extend.view_account_tuishuirld_form').id
        return {
            'name': '退税申报表',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view, 'form')],
            'res_id': self.tuishuirld_id.id,
            'target': 'current',
            'type': 'ir.actions.act_window',

            'context': {
                        }

        }



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

    @api.depends('declaration_amount', 'invoice_amount_total','invoice_residual_total')
    def compute_diff_tax(self):
        for one in self:
            diff_tax = one.declaration_amount - one.invoice_residual_total
            diff_origin_tax = one.declaration_amount - one.invoice_amount_total
            one.diff_tax = diff_tax
            one.diff_origin_tax = diff_origin_tax

    btd_id = fields.Many2one('back.tax.declaration',u'退税申报单',ondelete='cascade',  required=True)
    invoice_id = fields.Many2one('account.invoice',u'账单', required=True)
    tenyale_name = fields.Char(u'天宇编号',related='invoice_id.tenyale_name')
    invoice_back_tax_declaration_state = fields.Selection([('10','未申报'),('20','已申报')],'退税申报状态',related='invoice_id.back_tax_declaration_state')
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    invoice_amount_total = fields.Monetary(u'账单原始金额',currency_field='invoice_currency_id',compute=compute_invoice_amount_total,store=True)
    invoice_residual_total = fields.Monetary(u'账单剩余金额',currency_field='invoice_currency_id',compute=compute_invoice_residual,store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='btd_id.company_id', store=True, readonly=True, related_sudo=False)
    declaration_amount = fields.Monetary(u'退税申报金额',currency_field='invoice_currency_id')
    diff_tax = fields.Monetary(u'申报和剩余应收差额',currency_field='invoice_currency_id',compute='compute_diff_tax',store=True)
    diff_origin_tax = fields.Monetary(u'申报和原始应收差额', currency_field='invoice_currency_id', compute='compute_diff_tax',
                               store=True)
    declaration_amount_residual = fields.Monetary(u'未收款申报金额',currency_field='invoice_currency_id',compute=compute_declaration_amount_residual,store=True)
    comments = fields.Text(u'备注')
    invoice_attribute_all_in_one = fields.Selection(invoice_attribute_all_in_one, u'账单属性all_in_one',
                                                    related='invoice_id.invoice_attribute_all_in_one', store=True)
    back_tax_type = fields.Selection([('normal', u'正常退税'),
                                      ('adjustment', u'调节退税'),
                                      ], string=u'退税类型', related='invoice_id.back_tax_type',store=True)
    is_adjustment = fields.Boolean(u'是否已调节',related='invoice_id.is_adjustment',store=True)
    tuishuirld_id = fields.Many2one('account.payment', u'退税申报认领单')
    rcsktsrld_id = fields.Many2one('account.payment', u'收款退税账单认领')
    # def _default_name(self):
    #     line_name = self.env['ir.sequence'].next_by_code('back.tax.declaration.line.name')
    #     return line_name

    line_name = fields.Char(u'账单排序编号', related='invoice_id.line_name', store=True)



    back_tax_all_in_one_invoice = fields.Many2one('account.invoice',u'账单')







#####################################################################################################################
