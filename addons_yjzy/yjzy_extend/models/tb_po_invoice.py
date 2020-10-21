# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree

class tb_po_invoice(models.Model):
    _name = 'tb.po.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Invoice Apply'
    _order = 'id desc'

    @api.depends('hsname_all_ids', 'hsname_all_ids.purchase_amount2_add_this_time', 'hsname_all_ids.p_s_add_this_time','hsname_all_ids.tax_rate_add','hsname_all_ids.expense_tax',
                 'partner_id','extra_invoice_line_ids','extra_invoice_line_ids.price_unit','tb_id')
    def compute_info(self):
        for one in self:
            purchase_amount2_add_this_time_total = sum(x.purchase_amount2_add_this_time for x in one.hsname_all_ids)
            p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
            back_tax_add_this_time_total = sum(x.back_tax_add_this_time for x in one.hsname_all_ids)
            expense_tax = sum(x.expense_tax for x in one.hsname_all_ids)
            yjzy_invoice_id = one.tb_id.purchase_invoice_ids.filtered(lambda x: x.partner_id == one.partner_id and x.invoice_attribute in ['normal',False])
            # if len(purchase_invoice_partner_id) != 0:
            yjzy_invoice_residual_amount = sum(x.residual for x in yjzy_invoice_id)
            yjzy_invoice_include_tax = yjzy_invoice_id and yjzy_invoice_id[0].include_tax or False
            p_s_add_this_time_refund = 0.0
            if not yjzy_invoice_include_tax:
                if yjzy_invoice_residual_amount - p_s_add_this_time_total > 0:
                    p_s_add_this_time_refund = p_s_add_this_time_total
                else:
                    p_s_add_this_time_refund = yjzy_invoice_residual_amount
            p_s_add_this_time_extra_total = p_s_add_this_time_total - p_s_add_this_time_refund
            amount_diff = back_tax_add_this_time_total + p_s_add_this_time_total - purchase_amount2_add_this_time_total

            if one.type in ['extra','other_payment']:
                price_total = sum(one.extra_invoice_line_ids.mapped('price_total'))
                one.price_total = price_total
            else:
                one.price_total = purchase_amount2_add_this_time_total
            one.expense_tax = expense_tax
            one.p_s_add_this_time_extra_total = p_s_add_this_time_extra_total
            one.p_s_add_this_time_refund = p_s_add_this_time_refund
            one.purchase_amount2_add_this_time_total = purchase_amount2_add_this_time_total
            one.p_s_add_this_time_total = p_s_add_this_time_total
            one.back_tax_add_this_time_total = back_tax_add_this_time_total
            one.amount_diff = amount_diff
            one.yjzy_invoice_residual_amount = yjzy_invoice_residual_amount
            one.yjzy_invoice_include_tax = yjzy_invoice_include_tax
            # one.yjzy_invoice_id = yjzy_invoice_id and yjzy_invoice_id[0] or False

    #825
    # @api.depends('extra_invoice_line_ids','extra_invoice_line_ids.price_unit')
    # def compute_price_total(self):
    #     price_total = 0.0
    #     for one in self:
    #         price_total = sum(one.extra_invoice_line_ids.mapped('price_total'))
    #         one.price_total = price_total
        # 825

    def _default_currency_id(self):
        return self.env.user.company_id.currency_id.id

    def _default_extra_invoice_line(self): #参考one2many的default 默认
        default_yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        default_type = self.env.context.get('default_type')
        res = []
        # yjzy_type_1=self.env.context.get('yjzy_type_1')
        # type = self.env.context.get('type')
        product = self.env['product.product'].search([('for_other_po','=',True)])
        print('default_yjzy_type_1',default_yjzy_type_1,default_type)
        for line in product:
            if default_yjzy_type_1 == 'purchase' and default_type == 'other_po':
                res.append((0, 0, {
                    'product_id': line.id
                }))
        return res or None

    # @api.onchange('partner_id')
    # def onchange_extra_invoice_line(self):
    #     res = []
    #     type_obj = self.env['packaging.type']
    #     yjzy_type_1=self.yjzy_type_1
    #     type = self.type
    #     if yjzy_type_1 == 'purchase' and type == 'other_po':
    #         res.append((0, 0, {
    #             'product_id':self.env.ref('yjzy_extend.product_qtyfk').id
    #         }))
    #     self.extra_invoice_line_ids = res
    # # invoice_ids = fields.Many2many('account.invoice','ref_invoice_tb','invoice_id','tbl_id',u'额外账单')
    # # hsname_id = fields.Many2one('tbl.hsname', u'报关明细')

    # @api.depends('hsname_all_ids','hsname_all_ids.tax_rate_add','hsname_all_ids.expense_tax')
    # def compute_expense_tax(self):
    #     for one in self:
    #         expense_tax = sum(x.expense_tax for x in one.hsname_all_ids)
    #         one.expense_tax = expense_tax

    def _default_feiyong_tax_product(self):
        try:
            #return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code','=', 'C1102280A')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None
    def _default_product_zyywsr(self):
        try:
            #return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code','=', '01000')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_product_qtysk(self):
        try:
            #return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code','=', 'D01938')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_product_back_tax(self):
        try:
            #return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code','=', 'back_tax')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_partner(self):
        ctx = self.env.context.get('default_type')
        partner = False
        if ctx == 'other_payment':
            partner = self.env['res.partner'].search([('name', '=', '未定义')], limit=1)
        return partner

    # @api.depends('name','name_title')
    # def compute_display_name(self):
    #     ctx = self.env.context
    #     res = []
    #     for one in self:
    #         if
    #         if ctx.get('default_sfk_type', '') == 'ysrld':
    #             name = '%s:%s' % (one.journal_id.name, str(one.balance))
    #         elif ctx.get('bank_amount'):
    #             name = '%s[%s]' % (one.journal_id.name, str(one.balance))
    #         elif ctx.get('advance_bank_amount'):
    #             name = '%s[%s]' % (one.yjzy_payment_id.journal_id.name, str(one.advance_balance_total))
    #         elif ctx.get('advance_so_amount'):
    #             if not one.yjzy_payment_id:
    #                 name = '%s[%s]' % (one.journal_id.name, str(one.balance))
    #             else:
    #                 if one.so_id:
    #                     name = '%s[%s]' % (one.so_id.contract_code, str(one.advance_balance_total))
    #                 else:
    #                     name = '%s[%s]' % ('无销售合同', str(one.advance_balance_total))
    #         elif ctx.get('advance_po_amount'):
    #             if not one.yjzy_payment_id:
    #                 name = '%s[%s]' % (one.journal_id.name, str(one.amount))
    #             else:
    #                 if one.po_id:
    #                     name = '%s[%s]' % (one.po_id.contract_code, str(one.advance_balance_total))
    #                 else:
    #                     name = '%s[%s]' % ('无采购合同', str(one.advance_balance_total))
    #         elif ctx.get('default_sfk_type', '') == 'yfsqd':
    #             name = '%s:%s' % (one.name, str(one.advance_balance_total))
    #         else:
    #             name = '%s[%s]' % (one.name, str(one.balance))
    #         print('ctx_1111', ctx)
    #         one.display_name = name

    #关联的申请单：其他应收对其他应付，其他应付对其他应收
    # payment_id = fields.Many2one('account.payment',u'收付款单')
    # display_name = fields.Char(u'显示名称', compute=compute_display_name)

    @api.depends('invoice_p_ids','invoice_s_ids','invoice_back_tax_ids.residual','invoice_p_s_ids.residual','invoice_p_s_ids.residual')
    def compute_residual(self):
        for one in self:
            po_add_residual = sum(i.residual for i in one.invoice_p_ids.filtered(lambda x: x.state == 'open'))
            p_s_add_residual = sum(i.residual for i in one.invoice_s_ids.filtered(lambda x: x.state == 'open'))
            back_tax_add_residual = sum(i.residual for i in one.invoice_back_tax_ids.filtered(lambda x: x.state == 'open'))
            p_s_add_refund_residual = sum(i.residual for i in one.invoice_p_s_ids.filtered(lambda x: x.state == 'open'))
            one.po_add_residual = po_add_residual
            one.p_s_add_residual = p_s_add_residual
            one.back_tax_add_residual = back_tax_add_residual
            one.p_s_add_refund_residual = p_s_add_refund_residual

    @api.depends('tb_id')
    def compute_tb_id_po_supplier(self):
        for one in self:
            tb_id_po_supplier = ''
            dlrs = one.tb_id.purchase_invoice_ids
            for o in dlrs:
                tb_id_po_supplier += '%s\n' % (o.partner_id.name)
            one.tb_id_po_supplier = tb_id_po_supplier

    def compute_invoice_count(self):
        for one in self:
            one.invoice_ids_count = len(one.invoice_ids)
            one.invoice_p_ids_count = len(one.invoice_p_ids)
            one.invoice_s_ids_count = len(one.invoice_s_ids)
            one.invoice_back_tax_ids_count = len(one.invoice_back_tax_ids)
            one.invoice_p_s_ids_count = len(one.invoice_p_s_ids)
            one.invoice_other_payment_ids_count = len(one.invoice_other_payment_ids)
            one.invoice_extra_ids_count = len(one.invoice_extra_ids)
            one.invoice_normal_ids_count = len(one.invoice_normal_ids)

    @api.depends('invoice_ids', 'invoice_ids.residual','invoice_ids.amount_total')
    def compute_invoice_amount(self):
        for one in self:
            invoice_normal_ids_residual = sum(x.residual for x in one.invoice_normal_ids)
            one.invoice_normal_ids_residual = invoice_normal_ids_residual

    @api.depends('yjzy_invoice_id','manual_currency_id')
    def compute_currency_id(self):
        for one in self:
            yjzy_invoice_id = one.yjzy_invoice_id
            manual_currency_id = one.manual_currency_id
            if yjzy_invoice_id:
                one.currency_id = yjzy_invoice_id and yjzy_invoice_id[0].currency_id
            else:
                one.currency_id = manual_currency_id


    @api.depends('yjzy_tb_po_invoice','yjzy_tb_po_invoice.price_total','yjzy_tb_po_invoice.invoice_normal_ids_residual','yjzy_tb_po_invoice.partner_id')
    def compute_yjzy_tb_po_invoice_amount(self):
        for one in self:
            one.yjzy_tb_po_invoice_amount = one.yjzy_tb_po_invoice.price_total
            one.yjzy_tb_po_invoice_residual = one.yjzy_tb_po_invoice.invoice_normal_ids_residual

    company_id = fields.Many2one('res.company', '公司', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    yjzy_tb_po_invoice = fields.Many2one('tb.po.invoice',u'关联应收付申请单')
    yjzy_tb_po_invoice_amount = fields.Monetary('关联应收付申请单金额',currency_field='currency_id', compute=compute_yjzy_tb_po_invoice_amount,store=True)
    yjzy_tb_po_invoice_residual = fields.Monetary('关联应收付申请单余额',currency_field='currency_id', compute=compute_yjzy_tb_po_invoice_amount,store=True)
    is_yjzy_tb_po_invoice = fields.Boolean('是否有对应账单', default=False)
    #902
    is_tb_hs_id = fields.Boolean('是否货款')
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    fk_journal_id = fields.Many2one('account.journal', u'日记账',domain=[('type', 'in', ['cash', 'bank'])])
    tb_id_po_supplier = fields.Text(compute=compute_tb_id_po_supplier, string='供应商')
    expense_tax_algorithm = fields.Selection([('divide', u'除'), ('multiply', u'乘')], string='税点算法', default='divide')
    #828
    po_add_residual = fields.Float(u'增加采购未付金额',compute=compute_residual,store=True)
    p_s_add_residual = fields.Float(u'应收未收金额',compute=compute_residual,store=True)
    back_tax_add_residual = fields.Float(u'退税未收金额',compute=compute_residual,store=True)
    p_s_add_refund_residual = fields.Float(u'直接抵扣未完成金额',compute=compute_residual,store=True)
    #827
    amount_diff = fields.Float('实际差额')
    tax_rate_add = fields.Float(u'增加采购税率')
    expense_tax = fields.Float(u'税费',compute=compute_info)
    product_feiyong_tax = fields.Many2one('product.product',u'税费产品',domain=[('type','=','service')], default=_default_feiyong_tax_product)
    product_zyywsr = fields.Many2one('product.product', u'主营收入产品', domain=[('type', '=', 'service')],default=_default_product_zyywsr)
    product_qtysk = fields.Many2one('product.product', u'其他应收产品', domain=[('type', '=', 'service')],default=_default_product_qtysk)
    product_back_tax = fields.Many2one('product.product', u'退税产品', domain=[('type', '=', 'service')],default=_default_product_back_tax)




    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
                                         readonly=True, states={'draft': [('readonly', False)]})
    type_invoice = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ],  index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')#825
    yjzy_type = fields.Selection([('sale', u'销售'), ('purchase', u'采购'), ('back_tax', u'退税')], string=u'发票类型')#825 对应生成的发票，不用利用原来出运生成的账单。所以这个也没用了
    yjzy_type_1 = fields.Selection([('sale', u'应付'), ('purchase', u'采购'), ('back_tax', u'退税')], string=u'发票类型')#825
    extra_invoice_line_ids = fields.One2many('extra.invoice.line', 'tb_po_id', u'账单明细',default=lambda self: self._default_extra_invoice_line())
    price_total = fields.Monetary('金额合计',currency_field='currency_id',compute=compute_info,store=True)


    state = fields.Selection([('10_draft',u'草稿'),('20_submit',u'已提交'),('30_done','审批完成'),('80_refuse',u'拒绝'),('90_cancel',u'取消')],u'状态',index=True, track_visibility='onchange', default='10_draft')
    type = fields.Selection([('reconcile', '核销账单'),('extra', '额外账单'), ('other_po', '直接增加'),('expense_po', u'费用转换'),('other_payment',u'其他收付')],u'类型')
    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('tb.po.invoice'))
    name_title = fields.Char(u'账单描述')
    invoice_partner = fields.Char(u'账单对象')
    tb_id = fields.Many2one('transport.bill', u'出运单')
    partner_id = fields.Many2one('res.partner', u'合作伙伴', default=lambda self: self._default_partner())
    hsname_all_ids = fields.One2many('tb.po.invoice.line', 'tb_po_id', u'报关明细',)
    invoice_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关发票')
    invoice_ids_count = fields.Integer('相关发票数量',compute=compute_invoice_count)

    invoice_normal_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '申请账单',
                                         domain=[('type', 'in', ['in_invoice','out_invoice']),'&',('yjzy_type_1', 'in', ['purchase','sale']),'|',
                                                 ('invoice_attribute','not in',['other_po']),'&',('yjzy_type_1', 'in', ['purchase']),
                                                 ('invoice_attribute','in',['other_po'])])
    invoice_normal_ids_count = fields.Integer('申请账单数量', compute=compute_invoice_count)
    invoice_normal_ids_residual = fields.Float('申请账单未付金额', compute=compute_invoice_amount, store=True)  # 让所有的付款都其中在这个字段下



    yjzy_invoice_id = fields.Many2one('account.invoice', '关联账单')
    currency_id = fields.Many2one('res.currency', '货币',  compute=compute_currency_id)#default=_default_currency_id
    manual_currency_id = fields.Many2one('res.currency', '货币',  default=_default_currency_id)




    invoice_other_payment_ids = fields.One2many('account.invoice','tb_po_invoice_id','其他应付账单',domain=[('type','=','in_invoice'),('yjzy_type_1','=','purchase'),
                                                                                                      ('invoice_attribute','=','other_payment')])
    invoice_other_payment_ids_count = fields.Integer('其他应付账单数量', compute=compute_invoice_count)

    invoice_extra_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '额外账单',
                                                domain=[('invoice_attribute', '=', 'extra')])
    invoice_extra_ids_count = fields.Integer('额外账单数量', compute=compute_invoice_count)
    invoice_p_ids = fields.One2many('account.invoice','tb_po_invoice_id','新增采购应付发票',domain=[('type','=','in_invoice'),('yjzy_type_1','=','purchase'),
                                                                                            ('invoice_attribute','=','other_po')])
    invoice_p_ids_count = fields.Integer('相关采购发票数量', compute=compute_invoice_count)


    invoice_s_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关应收发票',domain=[('type','=','out_invoice'),('yjzy_type_1','=','sale'),('invoice_attribute','in',['other_po'])])
    invoice_s_ids_count = fields.Integer('相关应收发票数量', compute=compute_invoice_count)



    invoice_back_tax_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关退税发票',domain=[('type','=','out_invoice'),('yjzy_type_1','=','back_tax')])
    invoice_back_tax_ids_count = fields.Integer('相关退税发票数量', compute=compute_invoice_count)

    invoice_p_s_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关冲减发票',domain=[('type','=','in_refund'),('yjzy_type_1','=','purchase')])
    invoice_p_s_ids_count = fields.Integer('相关冲减发票数量', compute=compute_invoice_count)




    company_id = fields.Many2one('res.company', '公司', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    purchase_amount2_add_this_time_total = fields.Float('本次增加采购金额', compute=compute_info)
    p_s_add_this_time_total = fields.Float('本次应收总金额', compute=compute_info)
    p_s_add_this_time_extra_total = fields.Float('本次额外应收金额', compute=compute_info)
    back_tax_add_this_time_total = fields.Float('本次退税金额', compute=compute_info)
    p_s_add_this_time_refund = fields.Float('本次冲减金额', compute=compute_info)
    invoice_product_id = fields.Many2one('product.product', u'账单项目')



    expense_sheet_id = fields.Many2one('hr.expense.sheet',u'费用报告')
    expense_currency_id = fields.Many2one('res.currency',related='expense_sheet_id.currency_id')
    expense_sheet_amount = fields.Float('费用报告金额',related='expense_sheet_id.total_amount')
    expense_po_amount = fields.Float('费用转应付金额')
    yjzy_invoice_residual_amount = fields.Float('原始未付总金额', compute=compute_info)
    yjzy_invoice_include_tax = fields.Boolean('原始采购是否含税', compute=compute_info)
    extra_invoice_include_tax = fields.Boolean('原始账单是否含税')



    def unlink(self):
        for one in self:
            if one.state != '30_done':
                one.invoice_ids.unlink()
                one.yjzy_tb_po_invoice.unlink()
            else:
                raise Warning('完成审批不允许删除！')






    def open_tb_yjzy_po_invoice_open(self):
        view = self.env.ref('yjzy_extend.tb_po_form')
        return {
            'name': _(u'对应其他应收申请'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': self.yjzy_tb_po_invoice.id,
            'context': {'open': True}

        }

    @api.multi
    def name_get(self):
        ctx = self.env.context
        res = []
        for one in self:
            if one.type == 'other_payment' and one.type_invoice == 'in_invoice':
                name = '%s:%s' % ('其他应付', one.name)
            else:
                name = one.name
            res.append((one.id, name))
        return res

    #014
    @api.onchange('yjzy_invoice_id')
    def onchange_yjzy_invoice_id(self):
        self.extra_invoice_include_tax = self.yjzy_invoice_id.include_tax
        # self.currency_id = self.yjzy_invoice_id.currency_id
    #825
    @api.onchange('extra_invoice_line_ids')
    def onchange_payment_currency(self):
        yjzy_type_1 = self.yjzy_type_1
        if yjzy_type_1 == 'sale' or yjzy_type_1 == 'back_tax':
            if self.price_total < 0:
                self.type_invoice = 'out_refund'
            else:
                self.type_invoice = 'out_invoice'
        else:
            if self.price_total < 0:
                self.type_invoice = 'in_refund'
            else:
                self.type_invoice = 'in_invoice'


    def action_submit(self):
        self.state = '20_submit'
        if self.type == 'other_po':
            self.apply()
        if self.type == 'expense_po':
            self.apply()
        if self.type == 'extra':
            # self.make_extra_invoice()
            self.apply() #1014
        if self.type == 'other_payment':
            # self.make_extra_invoice()
            self.apply() #1014
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.action_submit()

    def action_manager_approve(self):
        if self.type == 'expense_po':
            self.create_yfhxd()
            print('type', self.type)
        self.state = '30_done'
        for one in self.invoice_ids:
            one.action_invoice_open()
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.action_manager_approve()

    def action_refuse(self,reason):
        self.invoice_ids.unlink()
        self.state = '80_refuse'
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.invoice_ids.unlink()
            self.yjzy_tb_po_invoice.state = '80_refuse'
        for tb in self:
            tb.message_post_with_view('yjzy_extend.expense_sheet_template_refuse_reason',
                                      values={'reason': reason, 'name': self.name},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式

    # def action_cancel(self):
    #     if self.state in
    #     if self.state not in ['30_done']:
    #         if self.invoice_ids:
    #             for one in self.invoice_ids:
    #                one.action_invoice_cancel()
    #         self.invoice_ids.unlink()
    #         self.state = '90_cancel'
    #         self.yjzy_tb_po_invoice.action_cancel()

    def action_draft(self):
        self.state = '10_draft'
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.state = '10_draft'



    @api.onchange('expense_sheet_id')
    def onchange_expense_sheet_id(self):
        if self.type == 'expense_po':
            bill_id = self.expense_sheet_id.expense_line_ids.mapped('tb_id')
            self.tb_id = bill_id




    @api.onchange('tb_id')
    def onchange_tb_id(self):
        hsname_all_ids=self.tb_id.hsname_all_ids
        res=[]
        for line in hsname_all_ids:
            res.append((0, 0, {
                #akiny
                # 'hs_id':line.hs_id.id,
                # 'hs_en_name': line.hs_en_name,
                # 'back_tax':line.back_tax,
                # 'purchase_amount2_tax': line.purchase_amount2_tax,
                # 'purchase_amount2_no_tax': line.purchase_amount2_no_tax,
                # 'purchase_amount_max_add_forecast': line.purchase_amount_max_add_forecast,
                # 'purchase_amount_min_add_forecast': line.purchase_amount_min_add_forecast,
                # 'purchase_amount_max_add_rest': line.purchase_amount_max_add_rest,
                # 'purchase_amount_min_add_rest': line.purchase_amount_min_add_rest,
                'hsname_all_line_id': line.id
            }))
        yjzy_invoice_id = self.tb_id.purchase_invoice_ids.filtered(
            lambda x: x.partner_id == self.partner_id)
        self.hsname_all_ids = res

        self.invoice_product_id = self.env.ref('yjzy_extend.product_qtyfk').id

        ctx = self.env.context.get('default_yjzy_invoice_id')
        print('ctx_oo', ctx)
        if not ctx:
            self.yjzy_invoice_id = yjzy_invoice_id and yjzy_invoice_id[0] or False

    @api.onchange('partner_id')
    def onchange_partner_id(self):
        ctx = self.env.context.get('default_yjzy_invoice_id')
        print('ctx_oo',ctx)
        if not ctx:
            yjzy_invoice_id = self.tb_id.purchase_invoice_ids.filtered(
                lambda x: x.partner_id == self.partner_id)
            self.yjzy_invoice_id = yjzy_invoice_id and yjzy_invoice_id[0] or False
            self.invoice_product_id = self.env.ref('yjzy_extend.product_qtyfk').id


    #
    # @api.onchange('hsname_all_ids')
    # def onchange_p_s_add_this_time(self):
    #     for one in self:
    #         p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
    #         yjzy_invoice_residual_amount = one.yjzy_invoice_residual_amount
    #         if yjzy_invoice_residual_amount - p_s_add_this_time_total > 0:
    #             p_s_add_this_time_refund = p_s_add_this_time_total
    #         else:
    #             p_s_add_this_time_refund = yjzy_invoice_residual_amount
    #         p_s_add_this_time_extra_total = p_s_add_this_time_total - p_s_add_this_time_refund
    #         one.p_s_add_this_time_extra_total = p_s_add_this_time_extra_total
    #         one.p_s_add_this_time_total = p_s_add_this_time_total
    #         one.p_s_add_this_time_refund = p_s_add_this_time_refund
    #
    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     purchase_invoice_partner_id = self.tb_id.purchase_invoice_ids.filtered(
    #         lambda x: x.partner_id == self.partner_id)
    #     print('purchase_invoice_partner_id', purchase_invoice_partner_id)
    #     # if len(purchase_invoice_partner_id) != 0:
    #     yjzy_invoice_residual_amount = sum(x.residual for x in purchase_invoice_partner_id)
    #     yjzy_invoice_include_tax = purchase_invoice_partner_id and purchase_invoice_partner_id[0].include_tax or False
    #     print('yjzy_invoice_residual_amount', yjzy_invoice_residual_amount, purchase_invoice_partner_id,
    #           self.tb_id.purchase_invoice_ids)
    #     self.yjzy_invoice_residual_amount = yjzy_invoice_residual_amount
    #     self.yjzy_invoice_include_tax = yjzy_invoice_include_tax
    #     self.yjzy_invoice_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0] or False



    def apply(self):
        self.ensure_one()
        if self.type == 'other_po':
            self.invoice_ids.unlink()
            self.make_purchase_invoice()
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()
        if self.type =='expense_po':
            self.invoice_ids.unlink()
            self.apply_expense_sheet()
            # self.make_extra_invoice()
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()
        if self.type == 'extra':
            self.invoice_ids.unlink()
            self.make_extra_invoice()
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()
        if self.type == 'other_payment':
            self.invoice_ids.unlink()
            self.make_other_payment_invoice()
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()

    def create_tb_po_invoice(self):
        self.ensure_one()
        line_tb_id = self.extra_invoice_line_ids
        if self.type == 'other_payment' and self.yjzy_type_1 == 'purchase':
            yjzy_type_1 = 'sale'
            type_invoice = 'out_invoice'
        elif self.type == 'other_payment' and self.yjzy_type_1 == 'sale':
            yjzy_type_1 = 'purchase'
            type_invoice = 'in_invoice'

        tb_po_id = self.env['tb.po.invoice'].create({'tb_id': self.tb_id.id,
                                                     'tax_rate_add': self.tax_rate_add,
                                                     'type': self.type,
                                                     'yjzy_type_1': yjzy_type_1,
                                                     'manual_currency_id':self.manual_currency_id.id,
                                                     'is_tb_hs_id':self.is_tb_hs_id,
                                                     'currency_id': self.currency_id.id,
                                                     'type_invoice':type_invoice
                                                     })

        view = self.env.ref('yjzy_extend.tb_po_form')
        line_obj = self.env['tb.po.invoice.line']
        extra_invoice_line_obj = self.env['extra.invoice.line']
        for hsl in self.hsname_all_ids:
            line_obj.create({
                'tb_po_id': tb_po_id.id,
                'hs_id': hsl.hs_id.id,
                'hs_en_name': hsl.hs_en_name,
                'purchase_amount2_tax': hsl.purchase_amount2_tax,
                'purchase_amount2_no_tax': hsl.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast': hsl.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast': hsl.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest': hsl.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest': hsl.purchase_amount_min_add_rest,
                'purchase_back_tax_amount2_new': hsl.purchase_back_tax_amount2_new,
                'hsname_all_line_id': hsl.id,
                'back_tax': hsl.back_tax
            })
        for line in self.extra_invoice_line_ids:
            product = line.product_id
            account = product.property_account_income_id
            # print('account', account)
            extra_invoice_line_obj.create({
                'tb_po_id': tb_po_id.id,
                'name': '%s' % (product.name),
                'product_id': product.id,
                'quantity': line.quantity,
                'price_unit': line.price_unit,
                'account_id': account.id

            })
        self.yjzy_tb_po_invoice = tb_po_id
        self.is_yjzy_tb_po_invoice = True

        return {
            'name': _(u'对应其他应收申请'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': tb_po_id.id,
            'context':{'open':True}

        }

    def delete_tb_po_invoice(self):
        if self.yjzy_tb_po_invoice and self.yjzy_tb_po_invoice.state in ['10_draft','80_refuse','90_cancel']:
            self.yjzy_tb_po_invoice.unlink()
            self.is_yjzy_tb_po_invoice = False


    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}
        # return {
        #     'name': _(u'创建费用转货款申请'),
        #     'view_type': 'tree,form',
        #     "view_mode": 'form',
        #     'res_model': 'tb.po.invoice',
        #     'type': 'ir.actions.act_window',
        #     'view_id': view.id,
        #     'target': 'current',
        #     'res_id': tb_po_id.id,
        #     # 'context': { },
        # }
    #应付发票
    def make_purchase_invoice(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']

        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        product_zyywsr = self.product_zyywsr
        product_qtysk = self.product_qtysk
        product_feiyong_tax = self.product_feiyong_tax
        account = product.property_account_income_id
        account_product_zyywsr = product_zyywsr.property_account_income_id
        account_product_qtysk = product_qtysk.property_account_income_id
        account_product_feiyong_tax = product_feiyong_tax.property_account_income_id

        # account_domain = [('code', '=', '2202'), ('company_id', '=', self.env.user.company_id.id)]
        # account_id = self.env['account.account'].search(account_domain, limit=1)
        # if account_id == False:
        #     raise Warning('请先设置额外账单的科目')
        print('yjzy_invoice_id',self.yjzy_invoice_id,)
        if self.purchase_amount2_add_this_time_total != 0:
            inv = invoice_obj.create({
                'tb_po_invoice_id':self.id,
                'partner_id': self.partner_id.id,
                'type': 'in_invoice',
                'journal_type': 'purchase',
                'bill_id': self.tb_id.id,
                'invoice_attribute':'other_po',
                'yjzy_type_1': 'purchase',
                'yjzy_payment_term_id':self.yjzy_invoice_id.payment_term_id.id,
                'yjzy_currency_id':self.currency_id.id,
                # 'payment_term_id': self.yjzy_invoice_id.payment_term_id.id,
                # 'currency_id': self.yjzy_invoice_id.currency_id.id,
                'date':fields.datetime.now(),
                'date_invoice':fields.datetime.now(),
                'date_finish': self.yjzy_invoice_id.date_finish,
                'po_id':self.yjzy_invoice_id.po_id.id,
                # 'account_id':account_id.id,
                'invoice_line_ids': [(0, 0, {
                                   'name': '%s' % (product_zyywsr.name),
                                   'product_id': product_zyywsr.id,
                                   'quantity': 1,
                                   'price_unit': self.p_s_add_this_time_refund,
                                   'account_id': account_product_zyywsr.id,}),
                                     (0, 0, {
                                         'name': '%s' % (product_qtysk.name),
                                         'product_id': product_qtysk.id,
                                         'quantity': 1,
                                         'price_unit': self.p_s_add_this_time_extra_total,
                                         'account_id': account_product_qtysk.id,}),
                                     (0, 0, {
                                         'name': '%s' % (product_feiyong_tax.name),
                                         'product_id': product_feiyong_tax.id,
                                         'quantity': 1,
                                         'price_unit': self.expense_tax,
                                         'account_id': account_product_feiyong_tax.id,})
                                     ]

            })
            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                    'invoice_id': inv.id,
                    'hs_id': line.hs_id.id,
                    'hs_en_name':line.hs_en_name,
                    'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
                    'p_s_add_this_time': line.p_s_add_this_time,
                    'back_tax_add_this_time': line.back_tax_add_this_time,
                    'tbl_hsname_all_id':line.hsname_all_line_id.id
                })


    def make_back_tax(self):
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.product_feiyong_tax
        # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
        account = product.property_account_income_id

        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        if self.back_tax_add_this_time_total != 0:
            back_tax_invoice = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': partner.id,
                'type': 'out_invoice',
                'journal_type': 'sale',
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'yjzy_type_1': 'back_tax',
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'invoice_line_ids': [(0, 0, {
                    'name': '%s' % (product.name,),
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': self.back_tax_add_this_time_total,
                    'account_id': account.id,
                })]
            })
            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                    'invoice_id': back_tax_invoice.id,
                    'hs_id': line.hs_id.id,
                    'hs_en_name': line.hs_en_name,
                    'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })
    # 730 创建后直接过账 冲减发票
    def make_sale_invoice(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        # product = self.invoice_product_id
        product = self.product_zyywsr
        account = product.property_account_income_id
        if self.p_s_add_this_time_refund != 0:
            inv = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'type': 'in_refund',
                'yjzy_type_1':'purchase',
                'yjzy_invoice_id':self.yjzy_invoice_id.id,
                'journal_type': 'sale',
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'invoice_line_ids': [(0, 0, {
                    'name': '%s' % (product.name),
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': self.p_s_add_this_time_refund,
                    'account_id': account.id,
                })]
            })
            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                    'invoice_id': inv.id,
                    'hs_id': line.hs_id.id,
                    'hs_en_name': line.hs_en_name,
                    'tbl_hsname_all_id': line.hsname_all_line_id.id
                })

    def make_sale_invoice_extra(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        # product = self.invoice_product_id
        product = self.product_qtysk
        account = product.property_account_income_id
        if self.p_s_add_this_time_extra_total != 0:
            inv = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'type': 'out_invoice',
                'journal_type': 'sale',
                'yjzy_type_1': 'sale',
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'invoice_line_ids': [(0, 0, {
                    'name': '%s' % (product.name),
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': self.p_s_add_this_time_extra_total,
                    'account_id': account.id,
                })]
            })
            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                    'invoice_id': inv.id,
                    'hs_id': line.hs_id.id,
                    'hs_en_name': line.hs_en_name,
                    'tbl_hsname_all_id': line.hsname_all_line_id.id
                })
    #825 额外账单  #ctx = {'type': [pk.id], 'active_id': pk.id} withcontext(ctx)
    def make_extra_invoice(self):
        self.ensure_one()
        if self.price_total != self.purchase_amount2_add_this_time_total:
            raise Warning('增加采购的金额不等于额外账单的总金额！')
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()  
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        account = product.property_account_income_id
        ctx = {'type': self.type_invoice}
        inv = invoice_obj.with_context(ctx).create({
            'yjzy_invoice_id':self.yjzy_invoice_id.id,
            'tb_po_invoice_id': self.id,
            'partner_id': self.partner_id.id,
            'bill_id': self.yjzy_invoice_id.bill_id.id,
            'invoice_attribute': self.type,
            'type': self.type_invoice,
            'yjzy_type_1':self.yjzy_type_1,
            'yjzy_invoice_number': self.yjzy_invoice_id.number,
            'is_yjzy_invoice': True,
            'payment_term_id': self.yjzy_invoice_id.payment_term_id.id,
            'currency_id': self.currency_id.id,
            'include_tax': self.yjzy_invoice_id.include_tax,
            'date_ship': self.yjzy_invoice_id.date_ship,
            'date_finish': self.yjzy_invoice_id.date_finish,
            'date_invoice': self.yjzy_invoice_id.date_invoice,
            'date': self.yjzy_invoice_id.date,
            'date_out_in': self.yjzy_invoice_id.date_out_in,
            'gongsi_id': self.yjzy_invoice_id.gongsi_id.id,
            # 'invoice_line_ids': [(0, 0, {
            #     'name': '%s' % (product.name),
            #     'product_id': product.id,
            #     'quantity': 1,
            #     'price_unit': self.p_s_add_this_time_extra_total,
            #     'account_id': account.id,
            # })]
        })
        yjzy_type_1 = self.yjzy_type_1
        if yjzy_type_1 == 'sale' or yjzy_type_1 == 'back_tax':
            if self.price_total < 0:
                # self.type_invoice = 'out_refund' #好像没什么用
                for line in self.extra_invoice_line_ids:
                    price_unit = -line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })
            else:
                # self.type_invoice = 'out_invoice'
                for line in self.extra_invoice_line_ids:
                    price_unit = line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })
        else:
            if self.price_total < 0:
                # self.type_invoice = 'in_refund'
                for line in self.extra_invoice_line_ids:
                    price_unit = -line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                    #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })
            else:
                # self.type_invoice = 'in_invoice'
                for line in self.extra_invoice_line_ids:
                    price_unit = line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                    #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })
        inv._default_name()
        inv.compute_name_extra()
        form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_form').id
        return {
            'name': u'采购额外账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view, 'form')],
            'res_id': inv.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }

    #创建其他应付账单
    def make_other_payment_invoice(self):
        self.ensure_one()
        if self.purchase_amount2_add_this_time_total != 0 and self.price_total != self.purchase_amount2_add_this_time_total:
            raise Warning('开票金额不等于额外账单的总金额！')
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        account = product.property_account_income_id

        inv = invoice_obj.create({
            'yjzy_invoice_id':self.yjzy_invoice_id.id,
            'tb_po_invoice_id': self.id,
            'partner_id': self.partner_id.id,

            'invoice_attribute': self.type,
            'type': self.type_invoice,
            'yjzy_type_1':self.yjzy_type_1,
            'is_yjzy_invoice': False,
            'currency_id': self.currency_id.id,

            # 'invoice_line_ids': [(0, 0, {
            #     'name': '%s' % (product.name),
            #     'product_id': product.id,
            #     'quantity': 1,
            #     'price_unit': self.p_s_add_this_time_extra_total,
            #     'account_id': account.id,
            # })]
        })
        yjzy_type_1 = self.yjzy_type_1
        if yjzy_type_1 == 'sale' or yjzy_type_1 == 'back_tax':
            if self.price_total < 0:
                # self.type_invoice = 'out_refund' #好像没什么用
                for line in self.extra_invoice_line_ids:
                    price_unit = -line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })

            else:
                # self.type_invoice = 'out_invoice'
                for line in self.extra_invoice_line_ids:
                    price_unit = line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })

        else:
            if self.price_total < 0:
                # self.type_invoice = 'in_refund'
                for line in self.extra_invoice_line_ids:
                    price_unit = -line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                    #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })

            else:
                # self.type_invoice = 'in_invoice'
                for line in self.extra_invoice_line_ids:
                    price_unit = line.price_unit
                    invoice_line = invoice_line_obj.create({
                        'name': line.name,
                        'invoice_id': inv.id,
                        'product_id': line.product_id.id,
                        'price_unit': price_unit,
                        'quantity': line.quantity,
                        'tp_po_invoice_line': line.id,
                        'account_id': line.product_id.property_account_income_id.id
                    })
                    # invoice_line._onchange_product_id()
                    #1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })

        inv._default_name()
        inv.compute_name_extra()
        inv.yjzy_invoice_id = inv.id
        form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_form').id
        return {
            'name': u'采购额外账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views': [(form_view, 'form')],
            'res_id': inv.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }
    def apply_expense_sheet(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        account = product.property_account_income_id
        if self.purchase_amount2_add_this_time_total != 0:
            inv = invoice_obj.create({
                    'partner_id': self.partner_id.id,
                    'tb_po_invoice_id': self.id,
                    'bill_id': self.tb_id.id,
                    'invoice_attribute':'expense_po',
                    'expense_sheet_id':self.expense_sheet_id.id,
                    'type':'in_invoice',
                    'journal_type':'purchase',
                    'yjzy_type_1':'purchase',
                    'fk_journal_id': self.fk_journal_id.id,
                    'bank_id':self.bank_id.id,
                    'date': fields.datetime.now(),
                    'date_invoice': fields.datetime.now(),
                #     'invoice_line_ids': [(0, 0, {
                #                        'name': '%s' % (product.name),
                #                        'product_id': product.id,
                #                        'quantity': 1,
                #                        'price_unit': self.purchase_amount2_add_this_time_total,
                #                        'account_id': account.id,
                # })]
                })
            expense_line_ids = self.expense_sheet_id.expense_line_ids
            for line_1 in expense_line_ids:
                product = line_1.product_id
                account = product.property_account_income_id
                invoice_line = invoice_line_obj.create({
                    'name': '%s' % (product.name),
                    'invoice_id':inv.id,
                    'product_id':line_1.product_id.id,
                    'quantity':line_1.quantity,
                    'price_unit':line_1.unit_amount,
                    'account_id':account.id
                })

            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                                    'invoice_id': inv.id,
                                    'hs_id': line.hs_id.id,
                                    'hs_en_name':line.hs_en_name,
                                    'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
                                    'tbl_hsname_all_id':line.hsname_all_line_id.id
                })
            # self.expense_sheet_id.invoice_id = inv
            # form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_po_form').id
            # return {
            #     'name': u'增加采购额外账单',
            #     'view_type': 'form',
            #     'view_mode': 'form',
            #     'res_model': 'account.invoice',
            #     'views':[(form_view,'form')],
            #     'res_id':inv.id,
            #     'type': 'ir.actions.act_window',
            #     'target': 'new',
            #
            # }

    def create_yfhxd(self):
        self.invoice_back_tax_ids.action_invoice_open()
        self.invoice_p_ids.action_invoice_open()
        self.invoice_p_ids.create_yfhxd()
        # for one in self.invoice_back_tax_ids:
        #     one.action_invoice_open()
        # for one in self.invoice_p_ids:
        #     one.action_invoice_open()
        #     one.create_yfhxd()


class tb_po_invoice_line(models.Model):
    _name = 'tb.po.invoice.line'

    @api.depends('purchase_amount2_add_this_time','tax_rate_add','tb_po_id.expense_tax_algorithm')
    def compute_info(self):
        for one in self:
            tax_rate_add = one.tax_rate_add
            purchase_amount2_add_this_time = one.purchase_amount2_add_this_time
            expense_tax_algorithm = one.tb_po_id.expense_tax_algorithm
            expense_tax = 0.0
            if expense_tax_algorithm == 'multiply':
                expense_tax = purchase_amount2_add_this_time * tax_rate_add
            elif expense_tax_algorithm == 'divide':
                expense_tax = purchase_amount2_add_this_time - purchase_amount2_add_this_time / (1+ tax_rate_add)
            if one.tb_po_id.type == 'other_po':
                p_s_add_this_time = purchase_amount2_add_this_time - expense_tax
            else:
                p_s_add_this_time = 0
            one.expense_tax = expense_tax
            one.p_s_add_this_time = p_s_add_this_time

    @api.depends('purchase_amount2_add_this_time','tb_po_id.tax_rate_add')
    def compute_back_tax(self):
        for one in self:
            back_tax_add_this_time = one.purchase_amount2_add_this_time / 1.13 * one.back_tax
            one.back_tax_add_this_time = back_tax_add_this_time

    #902

    #827
    tax_rate_add = fields.Float(u'增加采购税率',related='tb_po_id.tax_rate_add')
    expense_tax = fields.Float(u'税费',compute=compute_info)
    tb_po_id = fields.Many2one('tb.po.invoice', 'TB_PO',ondelete='cascade')
    hsname_all_line_id = fields.Many2one('tbl.hsname.all', u'销售明细')
    hs_en_name = fields.Char(related='hs_id.en_name')
    hs_id2 = fields.Many2one('hs.hs', u'报关品名')
    out_qty2 = fields.Float('报关数量')
    price2 = fields.Float('报关价格', )


    suppliser_hs_amount = fields.Float('采购HS统计金额')

    # 销售hs统计同步采购hs统计

    purchase_amount2 = fields.Float('采购金额')  # 814需要优化
    purchase_back_tax_amount2 = fields.Float(u'报关退税税金额', )
    # hs_id = fields.Many2one('hs.hs', u'品名')
    # back_tax = fields.Float(u'退税率')
    # amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'))

    # purchase_amount2_tax = fields.Float(u'含税采购金额')
    # purchase_amount2_no_tax = fields.Float(u'不含税采购金额')
    # purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2))
    # purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2))
    # purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2))
    # purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2))
    # purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额')

    purchase_amount2_add_this_time = fields.Float(U'本次采购开票金额')
    p_s_add_this_time = fields.Float(u'本次应收金额' ,compute=compute_info)
    back_tax_add_this_time = fields.Float('本次应生成退税', compute=compute_back_tax)
    p_s_add_this_time_old = fields.Float(u'冲减原始应付金额')
    yjzy_invoice_id = fields.Many2one('account.invoice',u'关联账单')

    hs_id = fields.Many2one('hs.hs', u'品名',related='hsname_all_line_id.hs_id')
    back_tax = fields.Float(u'退税率',related='hsname_all_line_id.back_tax',store=True)
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'),related='hsname_all_line_id.amount2')
    purchase_amount2_tax = fields.Float(u'含税采购金额',related='hsname_all_line_id.purchase_amount2_tax')
    purchase_amount2_no_tax = fields.Float(u'不含税采购金额',related='hsname_all_line_id.purchase_amount2_no_tax')
    purchase_back_tax_amount2_new = fields.Float(u'原始退税金额',related='hsname_all_line_id.purchase_back_tax_amount2_new')#根据是否含税来进行计算
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_min_add_forecast')
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_max_add_forecast')
    purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_max_add_rest')
    purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_min_add_rest')
    purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额',related='hsname_all_line_id.purchase_amount2_add_actual')


    #830 退税的处理方式，手动要随hs_id但是自动又要和那边关联
    @api.onchange('hs_id')
    def onchange_hs_id(self):
        for one in self:
            one.back_tax = one.hs_id.back_tax

    #
    # @api.constrains('qty', 'supplier_id')
    # def check(self):
    #     if self.qty < 0:
    #         raise Warning(u'采购数量不能小于0')

class Extra_Invoice_Line(models.Model):
    _name = 'extra.invoice.line'
    _description = "Extra Invoice Line"
    @api.model
    def _default_account(self):
        if self._context.get('journal_id'):
            journal = self.env['account.journal'].browse(self._context.get('journal_id'))
            if self._context.get('type_invoice') in ('out_invoice', 'in_refund'):
                return journal.default_credit_account_id.id
            return journal.default_debit_account_id.id

    @api.one
    @api.depends('price_unit',  'quantity','product_id', 'tb_po_id.partner_id', 'tb_po_id.currency_id', 'tb_po_id.company_id',)
    def _compute_price(self):
        currency = self.tb_po_id and self.tb_po_id.currency_id or None
        price = self.price_unit
        self.price_subtotal = price_subtotal_signed =  self.quantity * price
        self.price_total =  self.price_subtotal
        sign = self.tb_po_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

    name = fields.Text(string='Description')
    sequence = fields.Integer(default=10,
                              help="Gives the sequence of this line when displaying the invoice.")
    tb_po_id = fields.Many2one('tb.po.invoice', string='TB_PO', ondelete='cascade',index=True)

    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account',
                                 required=True, domain=[('deprecated', '=', False)],
                                 default=_default_account,
                                 help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True, digits=dp.get_precision('Product Price'))
    price_subtotal = fields.Monetary(string='Amount',
                                     store=True, readonly=True, compute='_compute_price',
                                     help="Total amount without taxes")
    uom_id = fields.Many2one('product.uom', string='Unit of Measure',
                             ondelete='set null', index=True, oldname='uos_id')
    price_total = fields.Monetary(string='Amount',
                                  store=True, readonly=True, compute='_compute_price',
                                  help="Total amount with taxes")
    price_subtotal_signed = fields.Monetary(string='Amount Signed', currency_field='company_currency_id',
                                            store=True, readonly=True, compute='_compute_price',
                                            help="Total amount in the currency of the company, negative for credit note.")
    quantity = fields.Float(string='Quantity', digits=dp.get_precision('Product Unit of Measure'),
                            required=True, default=1)


    company_id = fields.Many2one('res.company', string='Company',
                                 related='tb_po_id.company_id', store=True, readonly=True, related_sudo=False)
    partner_id = fields.Many2one('res.partner', string='Partner',
                                 related='tb_po_id.partner_id', store=True, readonly=True, related_sudo=False)
    currency_id = fields.Many2one('res.currency', related='tb_po_id.currency_id', store=True, related_sudo=False)
    company_currency_id = fields.Many2one('res.currency', related='tb_po_id.company_currency_id', readonly=True,
                                              related_sudo=False)

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(Extra_Invoice_Line, self).fields_view_get(
            view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if self._context.get('type'):
            doc = etree.XML(res['arch'])
            for node in doc.xpath("//field[@name='product_id']"):
                if self._context['type'] in ('in_invoice', 'in_refund'):
                    # Hack to fix the stable version 8.0 -> saas-12
                    # purchase_ok will be moved from purchase to product in master #13271
                    if 'purchase_ok' in self.env['product.template']._fields:
                        node.set('domain', "[('purchase_ok', '=', True)]")
                else:
                    node.set('domain', "[('sale_ok', '=', True)]")
            res['arch'] = etree.tostring(doc, encoding='unicode')
        return res


    @api.v8
    def get_invoice_line_account(self, type, product, fpos, company):
        accounts = product.product_tmpl_id.get_product_accounts(fpos)
        if type in ('out_invoice', 'out_refund'):
            return accounts['income']
        return accounts['expense']

    @api.onchange('product_id')
    def _onchange_product_id(self):
        domain = {}
        if not self.tb_po_id:
            return

        part = self.tb_po_id.partner_id
        fpos = self.tb_po_id.fiscal_position_id
        company = self.tb_po_id.company_id
        currency = self.tb_po_id.currency_id
        type = self.tb_po_id.type_invoice

        if not part:
            warning = {
                    'title': _('Warning!'),
                    'message': _('You must first select a partner!'),
                }
            return {'warning': warning}

        if not self.product_id:
            if type not in ('in_invoice', 'in_refund'):
                self.price_unit = 0.0
            domain['uom_id'] = []
        else:
            # Use the purchase uom by default
            self.uom_id = self.product_id.uom_po_id
            if part.lang:
                product = self.product_id.with_context(lang=part.lang)
            else:
                product = self.product_id
            self.name = product.partner_ref
            account = self.get_invoice_line_account(type, product, fpos, company)
            if account:
                self.account_id = account.id


            if type in ('in_invoice', 'in_refund'):
                if product.description_purchase:
                    self.name += '\n' + product.description_purchase
            else:
                if product.description_sale:
                    self.name += '\n' + product.description_sale

            if not self.uom_id or product.uom_id.category_id.id != self.uom_id.category_id.id:
                self.uom_id = product.uom_id.id
            domain['uom_id'] = [('category_id', '=', product.uom_id.category_id.id)]

            if company and currency:
                if company.currency_id != currency:
                    self.price_unit = self.price_unit * currency.with_context(dict(self._context or {}, date=self.tb_po_id.date_invoice)).rate

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}





#####################################################################################################################
