# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree
from odoo.exceptions import UserError, ValidationError


class tb_po_invoice(models.Model):
    _name = 'tb.po.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = 'Invoice Apply'  # 发票申请单
    _order = 'id desc'

    @api.depends('hsname_all_ids', 'hsname_all_ids.purchase_amount2_add_this_time', 'hsname_all_ids.p_s_add_this_time',
                 'hsname_all_ids.tax_rate_add', 'hsname_all_ids.expense_tax','tax_rate_add','expense_tax_algorithm',
                 'partner_id', 'extra_invoice_line_ids', 'extra_invoice_line_ids.price_unit', 'tb_id',
                 'hsname_all_ids.back_tax_add_this_time', )
    def compute_info_store(self):
        for one in self:
            purchase_amount2_add_this_time_total = sum(x.purchase_amount2_add_this_time for x in one.hsname_all_ids)
            p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
            back_tax_add_this_time_total = sum(x.back_tax_add_this_time for x in one.hsname_all_ids)
            expense_tax = sum(x.expense_tax for x in one.hsname_all_ids)
            yjzy_invoice_id = one.tb_id.purchase_invoice_ids.filtered(
                lambda x: x.partner_id == one.partner_id and x.invoice_attribute in ['normal', False])
            # if len(purchase_invoice_partner_id) != 0:
            yjzy_invoice_residual_amount = sum(x.residual for x in yjzy_invoice_id)
            yjzy_invoice_include_tax = yjzy_invoice_id and yjzy_invoice_id[0].include_tax or False
            p_s_add_this_time_refund = 0.0
            # 暂时取消对未税采购的判断，不管含税或者未税，都生成应收和付款采购。最后做核销 1224
            # if not yjzy_invoice_include_tax:
            #     if yjzy_invoice_residual_amount - p_s_add_this_time_total > 0:
            #         p_s_add_this_time_refund = p_s_add_this_time_total
            #     else:
            #         p_s_add_this_time_refund = yjzy_invoice_residual_amount
            p_s_add_this_time_extra_total = p_s_add_this_time_total - p_s_add_this_time_refund
            amount_diff = back_tax_add_this_time_total + p_s_add_this_time_total - purchase_amount2_add_this_time_total
            if one.type in ['extra', 'other_payment']:
                # price_total = sum(one.extra_invoice_line_ids.mapped('price_total'))
                price_total = sum(x.price_total for x in one.extra_invoice_line_ids)
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

    def _default_currency_id(self):
        if self.yjzy_payment_id:
            return self.yjzy_payment_currency_id
        else:
            return self.env.user.company_id.currency_id.id

    def _default_extra_invoice_line(self):  # 参考one2many的default 默认核心参考
        not_is_default = self.env.context.get('not_is_default')
        default_yjzy_type_1 = self.env.context.get('default_yjzy_type_1')
        default_type = self.env.context.get('default_type')
        res = []
        if not_is_default:
            res = None
        else:
            # yjzy_type_1=self.env.context.get('yjzy_type_1')
            # type = self.env.context.get('type')
            if default_yjzy_type_1 == 'purchase' and default_type == 'other_po':
                product = self.env['product.product'].search([('for_other_po', '=', True)])
                print('default_yjzy_type_1', default_yjzy_type_1, default_type)
                for line in product:
                    if default_yjzy_type_1 == 'purchase' and default_type == 'other_po':
                        res.append((0, 0, {
                            'product_id': line.id
                        }))
            if default_yjzy_type_1 == 'other_payment_purchase' or self.yjzy_type_1 == 'other_payment_purchase':
                product = self.env['product.product'].search([('name', '=', '营业外支出')], limit=1)
                account = product.property_account_income_id
                res.append((0, 0, {
                    'name': '%s:%s' % (product.name, self.name),
                    'product_id': product.id,
                    'quantity': 1,
                    'account_id': account.id, }))
            if default_yjzy_type_1 == 'other_payment_sale' or self.yjzy_type_1 == 'other_payment_sale':
                product = self.env['product.product'].search([('name', '=', '营业外收入')], limit=1)
                account = product.property_account_income_id
                res.append((0, 0, {
                    'name': '%s:%s' % (product.name, self.name),
                    'product_id': product.id,
                    'quantity': 1,
                    'account_id': account.id, }))
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
            # return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code', '=', 'C1102280A')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_product_zyywsr(self):
        try:
            # return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code', '=', '01000')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_product_qtysk(self):
        try:
            # return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code', '=', 'D01938')], limit=1)
            print('===_default_feiyong_product===', p)
            return p.id

        except Exception as e:
            return None

    def _default_product_back_tax(self):
        try:
            # return self.env.ref('yjzy_extend.product_shuifei').id
            p = self.env['product.product'].search([('default_code', '=', 'back_tax')], limit=1)
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

    @api.depends('invoice_p_ids', 'invoice_s_ids', 'invoice_back_tax_ids.residual', 'invoice_p_s_ids.residual',
                 'invoice_p_s_ids.residual')
    def compute_residual(self):
        for one in self:
            po_add_residual = sum(i.residual for i in one.invoice_p_ids.filtered(lambda x: x.state == 'open'))
            p_s_add_residual = sum(i.residual for i in one.invoice_s_ids.filtered(lambda x: x.state == 'open'))
            back_tax_add_residual = sum(
                i.residual_signed for i in one.invoice_back_tax_ids.filtered(lambda x: x.state == 'open'))
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
            one.invoice_other_payment_in_ids_count = len(one.invoice_other_payment_in_ids)

    @api.depends('invoice_ids', 'invoice_ids.residual', 'invoice_ids.amount_total')
    def compute_invoice_amount(self):
        for one in self:
            invoice_normal_ids_residual = sum(x.residual_signed for x in one.invoice_normal_ids)
            one.invoice_normal_ids_residual = invoice_normal_ids_residual

    @api.depends('yjzy_invoice_id', 'manual_currency_id')
    def compute_currency_id(self):
        for one in self:

            yjzy_invoice_id = one.yjzy_invoice_id
            manual_currency_id = one.manual_currency_id
            if yjzy_invoice_id:
                one.currency_id = yjzy_invoice_id and yjzy_invoice_id[0].currency_id
            else:
                one.currency_id = manual_currency_id

    @api.depends('yjzy_tb_po_invoice', 'yjzy_tb_po_invoice.price_total',
                 'yjzy_tb_po_invoice.invoice_normal_ids_residual', 'yjzy_tb_po_invoice.partner_id')
    def compute_yjzy_tb_po_invoice_amount(self):
        for one in self:
            one.yjzy_tb_po_invoice_amount = one.yjzy_tb_po_invoice.price_total
            one.yjzy_tb_po_invoice_residual = one.yjzy_tb_po_invoice.invoice_normal_ids_residual

    @api.depends('yjzy_tb_po_invoice_parent', 'yjzy_tb_po_invoice_parent.price_total',
                 'yjzy_tb_po_invoice_parent.invoice_normal_ids_residual', 'yjzy_tb_po_invoice_parent.partner_id')
    def compute_yjzy_tb_po_invoice_parent_amount(self):
        for one in self:
            one.yjzy_tb_po_invoice_parent_amount = one.yjzy_tb_po_invoice_parent.price_total
            one.yjzy_tb_po_invoice_parent_residual = one.yjzy_tb_po_invoice_parent.invoice_normal_ids_residual

    def compute_tb_po_other_line_count(self):
        for one in self:
            tb_po_other_line_count = len(one.tb_po_other_line_ids)
            one.tb_po_other_line_count = tb_po_other_line_count

    @api.depends('name')
    def compute_display_name(self):
        ctx = self.env.context
        for one in self:
            if one.type == 'other_payment' and one.type_invoice == 'in_invoice':
                name = '%s:%s' % ('其他应付', one.name)
            elif one.type == 'other_payment' and one.type_invoice == 'out_invoice':
                name = '%s:%s' % ('其他应收', one.name)
            elif one.type == 'other_po':
                name = '%s:%s' % ('增加采购申请', one.name)
            else:
                name = one.name

            one.display_name = name

    @api.depends('invoice_other_payment_in_ids', 'invoice_other_payment_ids', 'invoice_other_payment_ids.residual',
                 'invoice_other_payment_in_ids.residual')
    def compute_other_residual(self):
        for one in self:
            if one.invoice_other_payment_ids and not one.invoice_other_payment_in_ids:
                other_payment_invoice_residual = sum(x.residual for x in one.invoice_other_payment_ids)
            else:
                other_payment_invoice_residual = sum(x.residual for x in one.invoice_other_payment_in_ids)
            one.other_payment_invoice_residual = other_payment_invoice_residual

    @api.depends('hsname_all_ids', 'hsname_all_ids.purchase_amount_min_add_rest_this_time')
    def compute_min_add_rest_this_time_total(self):
        for one in self:
            purchase_amount_min_add_rest_this_time_total = sum(
                x.purchase_amount_min_add_rest_this_time for x in one.hsname_all_ids)
            one.purchase_amount_min_add_rest_this_time_total = purchase_amount_min_add_rest_this_time_total



    #增加采购相关字段：


    purchase_amount_min_add_rest_this_time_total = fields.Float('审批前本次可增加合计', digits=(2, 2),
                                                                compute=compute_min_add_rest_this_time_total,
                                                                store=True)

    other_payment_invoice_residual = fields.Monetary('其他应收应付剩余金额', currency_field='currency_id',
                                                     compute=compute_other_residual, store=True)
    other_payment_invoice_residual_yjzy = fields.Monetary('关联其他应收付', currency_field='currency_id',
                                                          related='yjzy_tb_po_invoice.other_payment_invoice_residual')  # 下级
    other_payment_invoice_residual_yjzy_parent = fields.Monetary('关联其他应收付', currency_field='currency_id',
                                                                 related='yjzy_tb_po_invoice_parent.other_payment_invoice_residual')  # 上级

    # # 新增

    # 关联的申请单：其他应收对其他应付，其他应付对其他应收

    display_name = fields.Char(u'显示名称', compute=compute_display_name)

    price_total_yjzy_parent = fields.Monetary('金额合计', currency_field='currency_id',
                                              related='yjzy_tb_po_invoice_parent.price_total')  # 上级应收应付申请单的合计金额
    invoice_normal_ids_residual_yjzy_parent = fields.Float('对应账单申请账单未付金额',
                                                           related='yjzy_tb_po_invoice_parent.invoice_normal_ids_residual')
    currency_id_yjzy_parent = fields.Many2one('res.currency', related='yjzy_tb_po_invoice_parent.currency_id')
    yjzy_type_1_yjzy_parent = fields.Selection(
        [('sale', u'应付'), ('purchase', u'采购'), ('back_tax', u'退税'), ('other_payment_sale', '其他应收'),
         ('other_payment_purchase', '其他应付')], related='yjzy_tb_po_invoice_parent.yjzy_type_1', string=u'发票类型')  # 825
    is_yjzy_tb_po_invoice_yjzy_parent = fields.Boolean('是否有对应下级账单',
                                                       related='yjzy_tb_po_invoice_parent.is_yjzy_tb_po_invoice')
    is_yjzy_tb_po_invoice_parent_yjzy_parent = fields.Boolean('是否有对应上级账单',
                                                              related='yjzy_tb_po_invoice_parent.is_yjzy_tb_po_invoice_parent')
    invoice_partner_yjzy_parent = fields.Char(u'对应的应收付账单对象', related='yjzy_tb_po_invoice_parent.invoice_partner')
    name_title_yjzy_parent = fields.Char(u'对应的应收付账账单描述', related='yjzy_tb_po_invoice_parent.name_title')
    other_invoice_amount_yjzy_parent = fields.Monetary('对应的金额', currency_field='currency_id',
                                                       related='yjzy_tb_po_invoice_parent.other_invoice_amount')

    price_total_yjzy = fields.Monetary('金额合计', currency_field='currency_id', related='yjzy_tb_po_invoice.price_total')
    invoice_normal_ids_residual_yjzy = fields.Float('对应账单申请账单未付金额',
                                                    related='yjzy_tb_po_invoice.invoice_normal_ids_residual')
    currency_id_yjzy = fields.Many2one('res.currency', related='yjzy_tb_po_invoice.currency_id')
    yjzy_type_1_yjzy = fields.Selection(
        [('sale', u'应付'), ('purchase', u'采购'), ('back_tax', u'退税'), ('other_payment_sale', '其他应收'),
         ('other_payment_purchase', '其他应付')], related='yjzy_tb_po_invoice.yjzy_type_1', string=u'发票类型')  # 825

    is_yjzy_tb_po_invoice_yjzy = fields.Boolean('是否有对应下级账单', related='yjzy_tb_po_invoice.is_yjzy_tb_po_invoice')
    is_yjzy_tb_po_invoice_parent_yjzy = fields.Boolean('是否有对应上级账单',
                                                       related='yjzy_tb_po_invoice.is_yjzy_tb_po_invoice_parent')

    invoice_partner_yjzy = fields.Char(u'对应的应收付账单对象', related='yjzy_tb_po_invoice.invoice_partner')
    name_title_yjzy = fields.Char(u'对应的应收付账账单描述', related='yjzy_tb_po_invoice.name_title')
    other_invoice_amount_yjzy = fields.Monetary('对应的金额', currency_field='currency_id',
                                                related='yjzy_tb_po_invoice.other_invoice_amount')

    tb_po_other_line_ids = fields.One2many('extra.invoice.line', 'tb_po_other_id', u'关联明细')  # 上下级的其他应收应付对应的明细
    tb_po_other_line_count = fields.Integer(u'关联明细数量', compute=compute_tb_po_other_line_count)

    date_invoice = fields.Date('账单日期')
    yjzy_payment_id = fields.Many2one('account.payment', u'收付款单')
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'收款单未认领金额', related='yjzy_payment_id.balance',
                                           currency_field='yjzy_payment_currency_id', )
    yjzy_payment_amount = fields.Monetary(u'收款单未认领金额', related='yjzy_payment_id.amount',
                                          currency_field='yjzy_payment_currency_id', )

    gongsi_id = fields.Many2one('gongsi', '内部公司')
    yjzy_tb_po_invoice = fields.Many2one('tb.po.invoice', u'关联应收付下级申请单')
    yjzy_tb_po_invoice_parent = fields.Many2one('tb.po.invoice', u'关联应收付上级申请单')
    yjzy_tb_po_invoice_parent_amount = fields.Monetary('关联上级应收付申请单金额', currency_field='currency_id',
                                                       compute=compute_yjzy_tb_po_invoice_parent_amount, store=True)
    yjzy_tb_po_invoice_parent_residual = fields.Monetary('关联上级应收付申请单余额', currency_field='currency_id',
                                                         compute=compute_yjzy_tb_po_invoice_parent_amount, store=True)

    yjzy_tb_po_invoice_amount = fields.Monetary('关联应收付申请单金额', currency_field='currency_id',
                                                compute=compute_yjzy_tb_po_invoice_amount, store=True)
    yjzy_tb_po_invoice_residual = fields.Monetary('关联应收付申请单余额', currency_field='currency_id',
                                                  compute=compute_yjzy_tb_po_invoice_amount, store=True)
    is_yjzy_tb_po_invoice = fields.Boolean('是否有对应下级账单', default=False)
    is_yjzy_tb_po_invoice_parent = fields.Boolean('是否有对应上级账单', default=False)
    # 902
    is_tb_hs_id = fields.Boolean('是否货款')
    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    fk_journal_id = fields.Many2one('account.journal', u'日记账', domain=[('type', 'in', ['cash', 'bank'])])
    tb_id_po_supplier = fields.Text(compute=compute_tb_id_po_supplier, string='供应商')
    expense_tax_algorithm = fields.Selection([('divide', u'除'), ('multiply', u'乘')], string='税点算法', default='divide')
    # 828
    po_add_residual = fields.Float(u'增加采购未付金额', compute=compute_residual, store=True)
    p_s_add_residual = fields.Float(u'应收未收金额', compute=compute_residual, store=True)
    back_tax_add_residual = fields.Float(u'退税未收金额', compute=compute_residual, store=True)
    p_s_add_refund_residual = fields.Float(u'直接抵扣未完成金额', compute=compute_residual, store=True)
    # 827
    amount_diff = fields.Float('实际差额')
    tax_rate_add = fields.Float(u'增加采购税率',digits=(2,4))
    expense_tax = fields.Float(u'税费', compute=compute_info_store, store=True)
    product_feiyong_tax = fields.Many2one('product.product', u'税费产品', domain=[('type', '=', 'service')],
                                          default=_default_feiyong_tax_product)
    product_zyywsr = fields.Many2one('product.product', u'主营收入产品', domain=[('type', '=', 'service')],
                                     default=_default_product_zyywsr)
    product_qtysk = fields.Many2one('product.product', u'其他应收产品', domain=[('type', '=', 'service')],
                                    default=_default_product_qtysk)
    product_back_tax = fields.Many2one('product.product', u'退税产品', domain=[('type', '=', 'service')],
                                       default=_default_product_back_tax)

    fiscal_position_id = fields.Many2one('account.fiscal.position', string='Fiscal Position', oldname='fiscal_position',
                                         readonly=True, states={'draft': [('readonly', False)]})
    type_invoice = fields.Selection([
        ('out_invoice', 'Customer Invoice'),
        ('in_invoice', 'Vendor Bill'),
        ('out_refund', 'Customer Credit Note'),
        ('in_refund', 'Vendor Credit Note'),
    ], index=True, change_default=True,
        default=lambda self: self._context.get('type', 'out_invoice'),
        track_visibility='always')  # 825
    yjzy_type = fields.Selection([('sale', u'销售'), ('purchase', u'采购'), ('back_tax', u'退税')],
                                 string=u'发票类型')  # 825 对应生成的发票，不用利用原来出运生成的账单。所以这个也没用了
    yjzy_type_1 = fields.Selection(
        [('sale', u'应付'), ('purchase', u'采购'), ('back_tax', u'退税'), ('other_payment_sale', '其他应收'),
         ('other_payment_purchase', '其他应付')], string=u'发票类型')  # 825
    extra_invoice_line_ids = fields.One2many('extra.invoice.line', 'tb_po_id', u'账单明细',
                                             default=lambda self: self._default_extra_invoice_line())  # ,

    price_total = fields.Monetary('金额合计', currency_field='currency_id', compute=compute_info_store, store=True)

    state = fields.Selection(
        [('10_draft', u'草稿'), ('20_submit', u'已提交待审批'), ('30_done', '审批完成已生成账单'), ('80_refuse', u'拒绝'),
         ('90_cancel', u'取消')], u'状态', index=True, track_visibility='onchange', default='10_draft')
    type = fields.Selection([('reconcile', '核销账单'), ('extra', '额外账单'), ('other_po', '直接增加'), ('expense_po', u'费用转换'),
                             ('other_payment', u'其他收付')], u'类型')
    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('tb.po.invoice'))
    name_title = fields.Char(u'账单描述')
    invoice_partner = fields.Char(u'账单对象')
    tb_id = fields.Many2one('transport.bill', u'出运单')
    partner_id = fields.Many2one('res.partner', u'合作伙伴', default=lambda self: self._default_partner())
    hsname_all_ids = fields.One2many('tb.po.invoice.line', 'tb_po_id', u'报关明细', )
    invoice_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '相关发票')
    invoice_ids_count = fields.Integer('相关发票数量', compute=compute_invoice_count)

    # invoice_normal_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '申请账单',
    #                                      domain=['&',('yjzy_type_1', 'in', ['purchase','sale']),'|',
    #                                              ('invoice_attribute','not in',['other_po']),'&',('yjzy_type_1', 'in', ['purchase']),
    #                                              ('invoice_attribute','in',['other_po'])])#('type', 'in', ['in_invoice','out_invoice']),第一个

    invoice_normal_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '申请账单',
                                         domain=[('yjzy_type_1', 'in', ['purchase',
                                                                        'other_payment_purchase'])])  # ('type', 'in', ['in_invoice','out_invoice']),第一个
    invoice_normal_ids_count = fields.Integer('申请账单数量', compute=compute_invoice_count)
    invoice_normal_ids_residual = fields.Float('申请账单未付金额', compute=compute_invoice_amount,
                                               store=True)  # 让所有的付款都其中在这个字段下

    yjzy_invoice_id = fields.Many2one('account.invoice', '关联账单')
    yjzy_invoice_back_tax_id = fields.Many2one('account.invoice', u'关联退税账单')
    currency_id = fields.Many2one('res.currency', '货币', compute=compute_currency_id)  # default=_default_currency_id
    manual_currency_id = fields.Many2one('res.currency', '货币', default=_default_currency_id)

    invoice_other_payment_in_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '其他应收账单',
                                                   domain=[('type', '=', 'out_invoice'),
                                                           ('yjzy_type_1', 'in', ['sale', 'other_payment_sale']),
                                                           ('invoice_attribute', '=', 'other_payment')])
    invoice_other_payment_in_ids_count = fields.Integer('其他应收账单数量', compute=compute_invoice_count)

    invoice_other_payment_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '其他应付账单',
                                                domain=[('type', '=', 'in_invoice'),
                                                        ('yjzy_type_1', 'in', ['purchse', 'other_payment_purchase']),
                                                        ('invoice_attribute', '=', 'other_payment')])
    invoice_other_payment_ids_count = fields.Integer('其他应付账单数量', compute=compute_invoice_count)

    invoice_extra_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '额外账单',
                                        domain=[('invoice_attribute', '=', 'extra')])
    invoice_extra_ids_count = fields.Integer('额外账单数量', compute=compute_invoice_count)
    invoice_p_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '新增采购应付发票',
                                    domain=[('type', '=', 'in_invoice'), ('yjzy_type_1', '=', 'purchase'),
                                            ('invoice_attribute', 'in', ['other_po', 'expense_po'])])
    invoice_p_ids_count = fields.Integer('相关采购发票数量', compute=compute_invoice_count)

    invoice_s_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '相关应收发票',
                                    domain=[('type', '=', 'out_invoice'), ('yjzy_type_1', '=', 'sale'),
                                            ('invoice_attribute', 'in', ['other_po'])])
    invoice_s_ids_count = fields.Integer('相关应收发票数量', compute=compute_invoice_count)

    invoice_back_tax_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '相关退税发票',
                                           domain=[('type', 'in', ['out_invoice', 'out_refund']),
                                                   ('yjzy_type_1', '=', 'back_tax')])
    invoice_back_tax_ids_count = fields.Integer('相关退税发票数量', compute=compute_invoice_count)

    invoice_p_s_ids = fields.One2many('account.invoice', 'tb_po_invoice_id', '相关冲减发票',
                                      domain=[('type', '=', 'in_refund'), ('yjzy_type_1', '=', 'purchase')])
    invoice_p_s_ids_count = fields.Integer('相关冲减发票数量', compute=compute_invoice_count)
    company_id = fields.Many2one('res.company', '公司', required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    purchase_amount2_add_this_time_total = fields.Float('本次增加采购金额', compute=compute_info_store, store=True)
    p_s_add_this_time_total = fields.Float('本次应收总金额', compute=compute_info_store, store=True)
    p_s_add_this_time_extra_total = fields.Float('本次额外应收金额', compute=compute_info_store, store=True)
    back_tax_add_this_time_total = fields.Float('本次退税金额', compute=compute_info_store, store=True)
    p_s_add_this_time_refund = fields.Float('本次冲减金额', compute=compute_info_store, store=True)
    invoice_product_id = fields.Many2one('product.product', u'账单项目')

    other_invoice_amount = fields.Monetary('金额', currency_field='currency_id')

    expense_sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告', ondelete='cascade', index=True)
    expense_currency_id = fields.Many2one('res.currency', related='expense_sheet_id.currency_id')
    expense_sheet_amount = fields.Float('费用报告金额', related='expense_sheet_id.total_amount')
    expense_po_amount = fields.Float('费用转应付金额')
    yjzy_invoice_residual_amount = fields.Float('原始未付总金额', compute=compute_info_store, store=True)
    yjzy_invoice_include_tax = fields.Boolean('原始采购是否含税', compute=compute_info_store, store=True)
    extra_invoice_include_tax = fields.Boolean('原始账单是否含税')

    # 要让字段升级后，再进行添加 akiny参考 数据验证
    # @api.constrains('purchase_amount_min_add_rest_this_time_total','purchase_amount2_add_this_time_total')
    # def check_fields_one(self):
    #     for one in self:
    #         if one.purchase_amount2_add_this_time_total > one.purchase_amount_min_add_rest_this_time_total:
    #             raise Warning('增加采购金额不允许大于可增加采购金额')

    # @api.onchange('other_invoice_product_id')
    # def onchange_invoice_product_id(self):
    #     product = self.other_invoice_product_id
    #     account = product.property_account_income_id
    #     print('product_akiny',product)
    #     self.extra_invoice_line_ids = [(0, 0, {
    #                     'name': '%s:%s' % (product.name, self.name),
    #                     'product_id': product.id,
    #                     'quantity': 1,
    #                     'price_unit': self.other_invoice_amount,
    #                     'account_id': account.id,})]

    @api.onchange('other_invoice_amount')
    def onchange_other_invoice_amount(self):
        other_invoice_amount = self.other_invoice_amount
        self.extra_invoice_line_ids[0].price_unit = other_invoice_amount

    @api.onchange('other_invoice_amount_yjzy')
    def onchange_other_invoice_amoufnt_yjzy(self):
        if self.other_invoice_amount_yjzy:
            other_invoice_amount_yjzy = self.other_invoice_amount_yjzy
            self.tb_po_other_line_ids[0].price_unit = other_invoice_amount_yjzy

    # @api.onchange('other_invoice_amount_yjzy_parent')
    # def onchange_other_invoice_amount_yjzy_parent(self):
    #     other_invoice_amount_yjzy_parent = self.other_invoice_amount_yjzy_parent
    #     self.tb_po_other_line_ids[0].price_unit = other_invoice_amount_yjzy_parent

    def open_tb_po_invoice(self):
        form_view = self.env.ref('yjzy_extend.tb_po_form')
        return {
            'name': _(u'费用转换货'),
            'view_type': 'form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': form_view.id,
            'target': 'new',
            'res_id': self.id,
            'context': {}
        }

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment_id(self):
        self.manual_currency_id = self.yjzy_payment_currency_id

    @api.onchange('tax_rate_add')
    def onchange_tax_rate_add(self):
        if self.tax_rate_add >= 1:
            raise Warning('税率请填写小数！')

    def unlink(self):
        for one in self:
            if one.state not in ['20_submit', '30_done']:
                # if one.is_yjzy_tb_po_invoice_parent:
                #     raise Warning('该申请为下级申请，请转到对应的上级申请进行删除')
                one.invoice_ids.unlink()
                one.yjzy_tb_po_invoice.unlink()

            else:
                raise Warning('提交审批的申请不允许删除！')

        return super(tb_po_invoice, self).unlink()

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
            elif one.type == 'other_po':
                name = '%s:%s' % ('增加采购申请', one.name)
            else:
                name = one.name
            res.append((one.id, name))
        return res

    # 014
    @api.onchange('yjzy_invoice_id')
    def onchange_yjzy_invoice_id(self):
        self.extra_invoice_include_tax = self.yjzy_invoice_id.include_tax
        # self.currency_id = self.yjzy_invoice_id.currency_id

    # 825
    @api.onchange('extra_invoice_line_ids')
    def onchange_payment_currency(self):
        yjzy_type_1 = self.yjzy_type_1
        if yjzy_type_1 in ['sale', 'back_tax', 'other_payment_sale']:
            if self.price_total < 0:
                self.type_invoice = 'out_refund'
            else:
                self.type_invoice = 'out_invoice'
        else:
            if self.price_total < 0:
                self.type_invoice = 'in_refund'
            else:
                self.type_invoice = 'in_invoice'

    def action_tax_confirm(self):
        if self.type == 'other_po':
            if self.tax_rate_add == 0:
                view_id = self.env.ref('yjzy_extend.wizard_tb_po_tax_form').id
                return {
                    'name': '税点确认',
                    'type': 'ir.actions.act_window',
                    'view_type': 'form',
                    'view_mode': 'form',
                    'res_model': 'wizard.tb.po.invoice.tax',
                    'views': [(view_id, 'form')],
                    'target': 'new',
                    'context': {'default_tb_po_id': self.id},
                }
            else:
                # for one in self.hsname_all_ids:
                #     if one.purchase_amount2_add_this_time > one.purchase_amount_min_add_rest:
                #         raise Warning('增加金额不允许大于最新可增加金额！')
                if self.purchase_amount2_add_this_time_total == 0:
                    raise Warning('增加采购金额为0！')
                if not self.partner_id:
                    raise Warning('请选择新增对象供应商')
                self.action_submit()
        else:
            self.action_submit()

    @api.multi
    def action_submit(self):
        self.state = '20_submit'
        if self.type == 'other_po':
            # for one in self.hsname_all_ids:
            #     if one.purchase_amount2_add_this_time > one.purchase_amount_min_add_rest:
            #         raise Warning('增加金额不允许大于最新可增加金额！')
            if self.purchase_amount2_add_this_time_total == 0:
                raise Warning('增加采购金额为0！')
            if not self.partner_id:
                raise Warning('请选择新增对象供应商')
            self.apply()
        if self.type == 'expense_po':
            self.apply()
        if self.type == 'extra':
            # self.make_extra_invoice()
            self.apply()  # 1014
        if self.type == 'other_payment':
            # self.make_extra_invoice()
            self.apply()  # 1014
            if self.yjzy_type_1 == 'other_payment_sale' and not self.is_yjzy_tb_po_invoice and not self.is_yjzy_tb_po_invoice_parent:#0310 删除，提交其他应付的时候， 其他应收直接完成了审批
                self.action_manager_approve()
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.action_submit()

    def action_manager_approve(self):
        other_payment_invoice_id = False
        other_payment_invoice_parent_id = False
        # 做生成的账单之间的关联，需要再细化研究
        if self.is_yjzy_tb_po_invoice:
            if self.yjzy_type_1 in ['purchase', 'other_payment_purchase']:
                other_payment_invoice_id = self.yjzy_tb_po_invoice.invoice_other_payment_in_ids[0]
            else:
                other_payment_invoice_id = self.yjzy_tb_po_invoice.invoice_other_payment_ids[0]
        if self.is_yjzy_tb_po_invoice_parent:
            if self.yjzy_type_1 in ['sale', 'other_payment_sale']:
                other_payment_invoice_parent_id = self.yjzy_tb_po_invoice_parent.invoice_other_payment_ids[0]
            else:
                other_payment_invoice_parent_id = self.yjzy_tb_po_invoice_parent.invoice_other_payment_in_ids[0]
        # ------
        if self.type == 'expense_po':
            self.create_yfhxd()
            print('type', self.type)
        self.state = '30_done'
        if self.yjzy_tb_po_invoice:  # 有关联的下级其他应收或者其他应付申请单，让他也完成总经理审批
            self.yjzy_tb_po_invoice.action_manager_approve()
        if self.invoice_p_s_ids:
            for one in self.invoice_p_s_ids:
                one.invoice_assign_outstanding_credit()  # 如果是冲减的发票。直接核销。（目前不产生冲减的账单）
        if self.type == 'extra':  # 额外账单，暂时不用
            for one in self.invoice_extra_ids:
                if one.type in ['in_refund', 'out_refund']:
                    one.invoice_assign_outstanding_credit()
        # 如果是其他应收款，创建应收核销单，并直接完成总经理审批
        for one in self.invoice_ids:
            print('akiny_test', self.invoice_ids)
            one.action_invoice_open()
        if self.invoice_other_payment_in_ids:  # 所有的其他应收账单，如果申请单有yjzy_payment_id，直接完成认领
            if self.yjzy_payment_id:
                for one in self.invoice_other_payment_in_ids:
                    one.with_context({'default_yjzy_payment_id': self.yjzy_payment_id.id}).create_yshxd()
                    one.other_payment_invoice_id = other_payment_invoice_id
                    one.other_payment_invoice_parent_id = other_payment_invoice_parent_id
                    # for x in one.reconcile_order_ids:
                    #     x.action_manager_approve_stage()

    def action_other_paymnet_one_in_all(self):
        if self.type == 'other_payment':
            self.invoice_ids.unlink()
            self.make_other_payment_invoice()
        if self.yjzy_tb_po_invoice:
            self.yjzy_tb_po_invoice.invoice_ids.unlink()
            self.yjzy_tb_po_invoice.make_other_payment_invoice()
        # self.action_submit()
        self.action_manager_approve()

    def action_refuse(self, reason):
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
        hsname_all_ids = self.tb_id.hsname_all_ids
        res = []
        for line in hsname_all_ids:
            res.append((0, 0, {
                # akiny
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
        print('ctx_oo', ctx)
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
        if self.type == 'expense_po':
            if self.purchase_amount2_add_this_time_total != self.expense_sheet_amount:
                raise Warning('货款总金额不等于费用金额，请检查')
            self.invoice_ids.unlink()
            self.apply_expense_sheet()
            # self.make_extra_invoice()
            self.make_back_tax()
            # self.expense_sheet_id.with_context({'from_tb_po':1}).action_account_approve()
            # self.make_sale_invoice()
            # self.make_sale_invoice_extra()
        if self.type == 'extra':
            self.invoice_ids.unlink()
            self.make_extra_invoice()
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()
        if self.type == 'other_payment':
            if not self.invoice_partner:
                raise Warning('账单对象没有填写')
            if not self.name_title:
                raise Warning('账单描述没有填写')
            if not self.manual_currency_id:
                raise Warning('请选择货币')
            if len(self.extra_invoice_line_ids) == 0:
                raise Warning('请填写明细')
            self.invoice_ids.unlink()
            self.make_other_payment_invoice()
            # 下面三个不需要执行
            self.make_back_tax()
            self.make_sale_invoice()
            self.make_sale_invoice_extra()

    def create_tb_po_invoice(self):
        self.ensure_one()
        line_tb_id = self.extra_invoice_line_ids
        name = ''
        ctx = {}
        partner = self.env['res.partner'].search([('name', '=', '未定义')], limit=1)
        if self.type == 'other_payment' and self.yjzy_type_1 in ['purchase', 'other_payment_purchase']:
            if not self.name_title or not self.invoice_partner or not self.other_invoice_amount or not self.manual_currency_id:
                raise Warning('请先将信息填写完整')
            yjzy_type_1 = 'other_payment_sale'
            type_invoice = 'out_invoice'
            name = '创建其他应收申请'
        elif self.type == 'other_payment' and self.yjzy_type_1 in ['sale', 'other_payment_sale']:
            if not self.name_title or not self.invoice_partner or not self.other_invoice_amount or not self.manual_currency_id:
                raise Warning('请先将信息填写完整')
            yjzy_type_1 = 'other_payment_purchase'
            type_invoice = 'in_invoice'
            name = '创建其他应付申请'
            ctx = {'open': True,
                   'tb_po_invoice_old': self.id,
                   'open_other': 1}

        tb_po_id = self.env['tb.po.invoice'].with_context({'default_type': 'other_payment'}).create(
            {'tb_id': self.tb_id.id,
             'name_title': self.name_title,
             'invoice_partner': self.invoice_partner,
             'other_invoice_amount': self.other_invoice_amount,
             'tax_rate_add': self.tax_rate_add,
             'type': self.type,
             'yjzy_type_1': yjzy_type_1,
             'manual_currency_id': self.manual_currency_id.id,
             'is_tb_hs_id': self.is_tb_hs_id,
             'currency_id': self.currency_id.id,
             'type_invoice': type_invoice,
             'is_yjzy_tb_po_invoice_parent': True,
             'yjzy_tb_po_invoice_parent': self.id,
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
                'account_id': account.id,
                'tb_po_other_id': self.id,

            })
            line.tb_po_other_id = tb_po_id
        self.yjzy_tb_po_invoice = tb_po_id
        self.is_yjzy_tb_po_invoice = True

        return True
        # return {
        #     'name': _(name),
        #     'view_type': 'tree,form',
        #     "view_mode": 'form',
        #     'res_model': 'tb.po.invoice',
        #     'type': 'ir.actions.act_window',
        #     'view_id': view.id,
        #     'target': 'new',
        #     'res_id': tb_po_id.id,
        #     'context':ctx
        # }

    def open_wizard_create_order(self):
        self.ensure_one()
        if not self.invoice_partner:
            raise Warning('账单对象没有填写')
        if not self.name_title:
            raise Warning('账单描述没有填写')
        if not self.manual_currency_id:
            raise Warning('请选择货币')
        if len(self.extra_invoice_line_ids) == 0:
            raise Warning('请填写明细')
        ctx = self.env.context.copy()
        ctx.update({
            'default_tb_po_id': self.id,
            'default_is_yjzy_tb_po_invoice': self.is_yjzy_tb_po_invoice,
            'default_yjzy_type_1': self.yjzy_type_1
        })
        return {
            'name': '创建其他申请',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.create.other',
            # 'res_id': bill.id,
            'target': 'new',
            'type': 'ir.actions.act_window',
            'context': ctx,
        }

    def delete_tb_po_invoice(self):
        open = self.env.context.get('open_delete')
        if self.yjzy_tb_po_invoice and self.yjzy_tb_po_invoice.state in ['10_draft', '80_refuse', '90_cancel']:
            for one in self.yjzy_tb_po_invoice.extra_invoice_line_ids:
                one.unlink()
            self.yjzy_tb_po_invoice.unlink()
            self.is_yjzy_tb_po_invoice = False
            if open:
                view = self.env.ref('yjzy_extend.tb_po_form')
                return {
                    'name': _('创建其他应收申请'),
                    'view_type': 'tree,form',
                    "view_mode": 'form',
                    'res_model': 'tb.po.invoice',
                    'type': 'ir.actions.act_window',
                    'view_id': view.id,
                    'target': 'new',
                    'res_id': self.id,
                    'context': {}

                }

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

    def action_return_qtys(self):
        self.ensure_one()
        tb_po_invoice_old = self.env.context.get('tb_po_invoice_old')
        print('ctx_1111111111111111', tb_po_invoice_old)
        view = self.env.ref('yjzy_extend.tb_po_form')
        return {
            'name': _('其他应收申请'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': tb_po_invoice_old,
            'context': {
            }

        }

    # 应付发票
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
        print('yjzy_invoice_id', self.yjzy_invoice_id, )
        print('teset_akiny', account)
        if self.purchase_amount2_add_this_time_total != 0:
            inv = invoice_obj.with_context(
                {'default_type': 'in_invoice', 'type': 'in_invoice', 'journal_type': 'purchase'}).create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'type': 'in_invoice',
                'journal_type': 'purchase',
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'yjzy_type_1': 'purchase',
                'yjzy_payment_term_id': self.yjzy_invoice_id.payment_term_id.id,
                'yjzy_currency_id': self.currency_id.id,
                # 'payment_term_id': self.yjzy_invoice_id.payment_term_id.id,
                # 'currency_id': self.yjzy_invoice_id.currency_id.id,
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'date_finish': self.yjzy_invoice_id.date_finish,
                'po_id': self.yjzy_invoice_id.po_id.id,
                # 'account_id':account_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': '%s' % (product_zyywsr.name),
                    'product_id': product_zyywsr.id,
                    'quantity': 1,
                    'price_unit': self.p_s_add_this_time_refund,
                    'account_id': account_product_zyywsr.id, }),
                                     (0, 0, {
                                         'name': '%s' % (product_qtysk.name),
                                         'product_id': product_qtysk.id,
                                         'quantity': 1,
                                         'price_unit': self.p_s_add_this_time_extra_total,
                                         'account_id': account_product_qtysk.id, }),
                                     (0, 0, {
                                         'name': '%s' % (product_feiyong_tax.name),
                                         'product_id': product_feiyong_tax.id,
                                         'quantity': 1,
                                         'price_unit': self.expense_tax,
                                         'account_id': account_product_feiyong_tax.id, })
                                     ]

            })
            for line in self.hsname_all_ids:
                hsname_all_line = hsname_all_line_obj.create({
                    'invoice_id': inv.id,
                    'hs_id': line.hs_id.id,
                    'hs_en_name': line.hs_en_name,
                    'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                    'p_s_add_this_time': line.p_s_add_this_time,
                    'back_tax_add_this_time': line.back_tax_add_this_time,
                    'tbl_hsname_all_id': line.hsname_all_line_id.id
                })

    def make_back_tax(self):
        partner = self.env.ref('yjzy_extend.partner_back_tax')

        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.product_back_tax
        # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
        account = product.property_account_income_id
        payment_term_id = self.env.ref('yjzy_extend.account_payment_term_back_tax_14days')
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        print('teset_akiny', account)
        if not account:
            raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
        if self.back_tax_add_this_time_total > 0:
            back_tax_invoice = invoice_obj.with_context(
                {'default_type': 'out_invoice', 'type': 'out_invoice', 'journal_type': 'sale'}).create({
                'tb_po_invoice_id': self.id,
                'partner_id': partner.id,
                'type': 'out_invoice',
                'journal_type': 'sale',
                'bill_id': self.tb_id.id,
                'invoice_attribute': self.type,
                'yjzy_type_1': 'back_tax',
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'payment_term_id':payment_term_id.id,
                'yjzy_invoice_id': self.yjzy_invoice_back_tax_id.id,
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
            back_tax_invoice.create_tenyale_name()
        if self.back_tax_add_this_time_total < 0:
            back_tax_add_this_time_total = -self.back_tax_add_this_time_total
            back_tax_invoice = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': partner.id,
                'type': 'out_refund',
                'journal_type': 'sale',
                'bill_id': self.tb_id.id,
                'invoice_attribute': self.type,
                'yjzy_type_1': 'back_tax',
                'date': fields.datetime.now(),
                'date_invoice': fields.datetime.now(),
                'yjzy_invoice_id': self.yjzy_invoice_back_tax_id.id,
                'invoice_line_ids': [(0, 0, {
                    'name': '%s' % (product.name,),
                    'product_id': product.id,
                    'quantity': 1,
                    'price_unit': back_tax_add_this_time_total,
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
            back_tax_invoice.create_tenyale_name()

    # 730 创建后直接过账 冲减发票

    def make_sale_invoice(self):  # 再次检查
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
        print('teset_akiny', account)
        if self.p_s_add_this_time_refund != 0:
            inv = invoice_obj.with_context(
                {'default_type': 'in_refund', 'type': 'in_refund', 'journal_type': 'purchase'}).create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'type': 'in_refund',
                'yjzy_type_1': 'purchase',
                'yjzy_invoice_id': self.yjzy_invoice_id.id,
                'journal_type': 'purchase',
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
        print('teset_akiny', account)
        if self.p_s_add_this_time_extra_total != 0:
            inv = invoice_obj.with_context({'type': 'out_invoice', 'journal_type': 'sale'}).create({
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

    # 825 额外账单  #ctx = {'type': [pk.id], 'active_id': pk.id} withcontext(ctx)
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
        print('teset_akiny', account)
        if self.yjzy_type_1 in ['sale', 'back_tax', 'other_payment_sale']:
            journal_type = 'sale'
        else:
            journal_type = 'purchase'
        ctx = {'type': self.type_invoice,
               'journal_type': journal_type}
        inv = invoice_obj.with_context(ctx).create({
            'yjzy_invoice_id': self.yjzy_invoice_id.id,
            'tb_po_invoice_id': self.id,
            'partner_id': self.partner_id.id,
            'bill_id': self.yjzy_invoice_id.bill_id.id,
            'invoice_attribute': self.type,
            'type': self.type_invoice,
            'yjzy_type_1': self.yjzy_type_1,
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
        if yjzy_type_1 in ['sale', 'other_payment_sale', 'back_tax']:
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
                # 1014
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
                # 1014
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
                    # 1014
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
                    # 1014
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

    # 创建其他应付账单

    def make_other_payment_invoice(self):
        self.ensure_one()
        if self.purchase_amount2_add_this_time_total != 0 and self.price_total != self.purchase_amount2_add_this_time_total:
            raise Warning('开票金额不等于额外账单的总金额！')
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        product = self.invoice_product_id
        if self.yjzy_type_1 in ['sale', 'back_tax', 'other_payment_sale']:
            journal_type = 'sale'
        else:
            journal_type = 'purchase'
        print('journal_type_9999999999999', journal_type)
        print('teset_akiny', journal_type)
        inv = invoice_obj.with_context(
            {'default_type': self.type_invoice, 'type': self.type_invoice, 'journal_type': journal_type}).create({
            'invoice_partner': self.invoice_partner,
            'name_title': self.name_title,
            'yjzy_invoice_id': self.yjzy_invoice_id.id,
            'tb_po_invoice_id': self.id,
            'partner_id': self.partner_id.id,
            'journal_type': journal_type,
            'invoice_attribute': self.type,
            'type': self.type_invoice,
            'yjzy_type_1': self.yjzy_type_1,
            'is_yjzy_invoice': False,
            'currency_id': self.currency_id.id,
            'date': fields.datetime.now(),
            'date_invoice': fields.datetime.now(),
        })
        print('teset_akiny', '222222')
        yjzy_type_1 = self.yjzy_type_1
        if yjzy_type_1 in ['sale', 'back_tax', 'other_payment_sale']:
            print('teset_akiny', '222222')
            if self.price_total < 0:
                for line in self.extra_invoice_line_ids:
                    print('akiny_product', line.product_id.property_account_income_id.id)
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
                # 1014
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
                # print('teset_akiny', account)
                for line in self.extra_invoice_line_ids:
                    print('akiny_product_1', line.product_id.property_account_income_id.id)
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
                # 1014
                for line in self.hsname_all_ids:
                    hsname_all_line = hsname_all_line_obj.create({
                        'invoice_id': inv.id,
                        'hs_id': line.hs_id.id,
                        'hs_en_name': line.hs_en_name,
                        'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                        'tbl_hsname_all_id': line.hsname_all_line_id.id
                    })

        else:
            print('teset_akiny', '222222')
            if self.price_total < 0:
                # self.type_invoice = 'in_refund'
                for line in self.extra_invoice_line_ids:
                    print('akiny_product_3', line.product_id.property_account_income_id.id)
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
                    # 1014
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
                print('teset_akiny', 00000)
                for line in self.extra_invoice_line_ids:
                    print('akiny_product_2', line.product_id.property_account_income_id.id)
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
                    # 1014
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
        # if inv.invoice_attribute == 'other_payment':
        #     inv.action_invoice_open()
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

        journal_type = 'purchase'
        product = self.invoice_product_id
        account = product.property_account_income_id
        if self.purchase_amount2_add_this_time_total != 0:
            inv = invoice_obj.with_context(
                {'default_type': 'in_invoice', 'type': 'in_invoice', 'journal_type': 'purchase'}).create({
                'partner_id': self.partner_id.id,
                'tb_po_invoice_id': self.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'expense_po',
                'expense_sheet_id': self.expense_sheet_id.id,
                'type': 'in_invoice',
                'journal_type': journal_type,
                'yjzy_type_1': 'purchase',
                'fk_journal_id': self.fk_journal_id.id,
                'bank_id': self.bank_id.id,
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
                if product:
                    account = product.product_tmpl_id._get_product_accounts()['expense']
                    if not account:
                        raise UserError(
                            _(
                                "No Expense account found for the product %s (or for its category), please configure one.") % (
                                self.product_id.name))
                else:
                    account = self.env['ir.property'].with_context(force_company=self.company_id.id).get(
                        'property_account_expense_categ_id', 'product.category')
                    if not account:
                        raise UserError(
                            _(
                                'Please configure Default Expense account for Product expense: `property_account_expense_categ_id`.'))
                # account = product.property_account_income_id
                invoice_line = invoice_line_obj.create({
                    'name': '%s' % (product.name),
                    'invoice_id': inv.id,
                    'product_id': line_1.product_id.id,
                    'quantity': line_1.quantity,
                    'price_unit': line_1.unit_amount,
                    'account_id': account.id
                })
            # 1220 暂时取消这个，发票上明细不创建，那么就不会参与出运单的池子的计算
            # for line in self.hsname_all_ids:
            #     hsname_all_line = hsname_all_line_obj.create({
            #                         'invoice_id': inv.id,
            #                         'hs_id': line.hs_id.id,
            #                         'hs_en_name':line.hs_en_name,
            #                         'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
            #                         'tbl_hsname_all_id':line.hsname_all_line_id.id
            #     })
            # # self.expense_sheet_id.invoice_id = inv
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
    _name = 'tb.po.invoice.line'  # 增加采购明细，和出运合同的报关明细相关联 transport_bill2.create_tb_po_invoice

    @api.depends('purchase_amount2_add_this_time', 'tax_rate_add', 'tb_po_id.expense_tax_algorithm')
    def compute_info(self):
        for one in self:
            tax_rate_add = one.tax_rate_add
            purchase_amount2_add_this_time = one.purchase_amount2_add_this_time
            expense_tax_algorithm = one.tb_po_id.expense_tax_algorithm
            expense_tax = 0.0
            if expense_tax_algorithm == 'multiply':
                expense_tax = purchase_amount2_add_this_time * tax_rate_add
            elif expense_tax_algorithm == 'divide':
                expense_tax = purchase_amount2_add_this_time - purchase_amount2_add_this_time / (1 + tax_rate_add)
            if one.tb_po_id.type == 'other_po':
                p_s_add_this_time = purchase_amount2_add_this_time - expense_tax
            else:
                p_s_add_this_time = 0
            one.expense_tax = expense_tax
            one.p_s_add_this_time = p_s_add_this_time

    @api.depends('purchase_amount2_add_this_time', 'tb_po_id.tax_rate_add')
    def compute_back_tax(self):
        for one in self:
            back_tax_add_this_time = one.purchase_amount2_add_this_time / 1.13 * one.back_tax
            one.back_tax_add_this_time = back_tax_add_this_time

    @api.depends('purchase_amount_min_add_rest_this_time', 'purchase_amount2_add_this_time')
    def compute_rest_after(self):
        for one in self:
            one.purchase_amount_min_add_rest_after = one.purchase_amount_min_add_rest_this_time - one.purchase_amount2_add_this_time

    # 902

    # 827
    tax_rate_add = fields.Float(u'增加采购税率', related='tb_po_id.tax_rate_add')
    expense_tax = fields.Float(u'税费', compute=compute_info)
    tb_po_id = fields.Many2one('tb.po.invoice', 'TB_PO', ondelete='cascade')
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
    p_s_add_this_time = fields.Float(u'本次应收金额', compute=compute_info)
    back_tax_add_this_time = fields.Float('本次应生成退税', compute=compute_back_tax)
    p_s_add_this_time_old = fields.Float(u'冲减原始应付金额')
    yjzy_invoice_id = fields.Many2one('account.invoice', u'关联账单')

    hs_id = fields.Many2one('hs.hs', u'品名', related='hsname_all_line_id.hs_id')
    back_tax = fields.Float(u'退税率', related='hsname_all_line_id.back_tax', store=True)
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'), related='hsname_all_line_id.amount2')
    purchase_amount2_tax = fields.Float(u'含税采购金额', related='hsname_all_line_id.purchase_amount2_tax')
    purchase_amount2_no_tax = fields.Float(u'不含税采购金额', related='hsname_all_line_id.purchase_amount2_no_tax')
    purchase_back_tax_amount2_new = fields.Float(u'原始退税金额',
                                                 related='hsname_all_line_id.purchase_back_tax_amount2_new')  # 根据是否含税来进行计算
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2),
                                                    related='hsname_all_line_id.purchase_amount_min_add_forecast')
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2),
                                                    related='hsname_all_line_id.purchase_amount_max_add_forecast')
    purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2),
                                                related='hsname_all_line_id.purchase_amount_max_add_rest')
    purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2),
                                                related='hsname_all_line_id.purchase_amount_min_add_rest')
    purchase_amount_min_add_rest_this_time = fields.Float('审批前本次可增加', digits=(2, 2))
    purchase_amount_min_add_rest_after = fields.Float('审批后本次可增加', digits=(2, 2), compute=compute_rest_after)
    purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额', related='hsname_all_line_id.purchase_amount2_add_actual')

    # 830 退税的处理方式，手动要随hs_id但是自动又要和那边关联
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
    @api.depends('price_unit', 'quantity', 'product_id', 'tb_po_id.partner_id', 'tb_po_id.currency_id',
                 'tb_po_id.company_id', )
    def _compute_price(self):
        currency = self.tb_po_id and self.tb_po_id.currency_id or None
        price = self.price_unit
        self.price_subtotal = price_subtotal_signed = self.quantity * price
        self.price_total = self.price_subtotal
        sign = self.tb_po_id.type in ['in_refund', 'out_refund'] and -1 or 1
        self.price_subtotal_signed = price_subtotal_signed * sign

    tb_po_other_id = fields.Many2one('tb.po.invoice', u'对应的其他应收付', ondelete='set null')
    name = fields.Text(string='Description')
    sequence = fields.Integer(default=10,
                              help="Gives the sequence of this line when displaying the invoice.")
    tb_po_id = fields.Many2one('tb.po.invoice', string='TB_PO', ondelete='cascade', index=True)

    product_id = fields.Many2one('product.product', string='Product',
                                 ondelete='restrict', index=True)
    account_id = fields.Many2one('account.account', string='Account',
                                 required=True, domain=[('deprecated', '=', False)],
                                 default=_default_account,
                                 help="The income or expense account related to the selected product.")
    price_unit = fields.Float(string='Unit Price', required=True,
                              digits=(2, 2))  # digits=dp.get_precision('Product Price')
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

    comments = fields.Text(u'备注')

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
                    self.price_unit = self.price_unit * currency.with_context(
                        dict(self._context or {}, date=self.tb_po_id.date_invoice)).rate

                if self.uom_id and self.uom_id.id != product.uom_id.id:
                    self.price_unit = product.uom_id._compute_price(self.price_unit, self.uom_id)
        return {'domain': domain}

#####################################################################################################################
