# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp


class tb_po_invoice(models.Model):
    _name = 'tb.po.invoice'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '额外增加采购单'
    _order = 'id desc'

    @api.depends('hsname_all_ids', 'hsname_all_ids.purchase_amount2_add_this_time', 'hsname_all_ids.p_s_add_this_time',
                 'partner_id')
    def compute_info(self):
        for one in self:
            purchase_amount2_add_this_time_total = sum(x.purchase_amount2_add_this_time for x in one.hsname_all_ids)
            p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
            back_tax_add_this_time_total = sum(x.back_tax_add_this_time for x in one.hsname_all_ids)
            purchase_invoice_partner_id = one.tb_id.purchase_invoice_ids.filtered(
                lambda x: x.partner_id == one.partner_id)
            # if len(purchase_invoice_partner_id) != 0:
            purchase_invoice_amount = sum(x.residual for x in purchase_invoice_partner_id)
            purchase_invoice_include_tax = purchase_invoice_partner_id and purchase_invoice_partner_id[
                0].include_tax or False
            p_s_add_this_time_refund = 0.0
            if not purchase_invoice_include_tax:
                if purchase_invoice_amount - p_s_add_this_time_total > 0:
                    p_s_add_this_time_refund = p_s_add_this_time_total
                else:
                    p_s_add_this_time_refund = purchase_invoice_amount
            p_s_add_this_time_extra_total = p_s_add_this_time_total - p_s_add_this_time_refund
            one.p_s_add_this_time_extra_total = p_s_add_this_time_extra_total
            one.p_s_add_this_time_refund = p_s_add_this_time_refund
            one.purchase_amount2_add_this_time_total = purchase_amount2_add_this_time_total
            one.p_s_add_this_time_total = p_s_add_this_time_total
            one.back_tax_add_this_time_total = back_tax_add_this_time_total

            one.purchase_invoice_amount = purchase_invoice_amount
            one.purchase_invoice_include_tax = purchase_invoice_include_tax
            one.purchase_invoice_origin_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0] or False
            one.currency_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0].currency_id or self.env.user.company_id.currency_id.id



    # invoice_ids = fields.Many2many('account.invoice','ref_invoice_tb','invoice_id','tbl_id',u'额外账单')
    # hsname_id = fields.Many2one('tbl.hsname', u'报关明细')
    state = fields.Selection([('10_draft',u'草稿'),('20_submit',u'已提交'),('30_done','审批完成'),('40_refuse',u'拒绝')],u'状态',index=True, track_visibility='onchange', default='10_draft')
    type = fields.Selection([('other_po','直接增加'),('expense_po','费用转换')],u'类型')
    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('tb.po.invoice'))
    tb_id = fields.Many2one('transport.bill', u'出运单')
    partner_id = fields.Many2one('res.partner', u'合作伙伴')
    hsname_all_ids = fields.One2many('tb.po.invoice.line', 'tb_po_id', u'报关明细',)
    invoice_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关发票')
    purchase_invoice_origin_id = fields.Many2one('account.invoice', '原始应付发票',compute=compute_info)
    currency_id = fields.Many2one('res.currency', compute=compute_info)
    invoice_p_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关采购发票',domain=[('type','=','in_invoice'),('yjzy_type','=','purchase')])
    invoice_s_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关应收发票',domain=[('type','=','out_invoice'),('yjzy_type','=','sale')])
    invoice_back_tax_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关退税发票',domain=[('type','=','out_invoice'),('yjzy_type','=','back_tax')])
    invoice_p_s_ids = fields.One2many('account.invoice','tb_po_invoice_id','相关冲减发票',domain=[('type','=','in_refund'),('yjzy_type','=','purchase')])

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
    purchase_invoice_amount = fields.Float('原始未付总金额', compute=compute_info)
    purchase_invoice_include_tax = fields.Boolean('原始采购是否含税', compute=compute_info)

    def action_submit(self):
        self.state = '20_submit'
    def action_manager_approve(self):
        self.state = '30_done'
        if self.type == 'other_po':
            self.apply()
        if self.type == 'expense_po':
            self.apply_expense_sheet()
    def action_refuse(self):
        self.state = '40_refuse'
    def action_draft(self):
        self.state = '10_draft'




    @api.onchange('tb_id')
    def onchange_tb_id(self):
        hsname_all_ids=self.tb_id.hsname_all_ids

        res=[]
        for line in hsname_all_ids:
            res.append((0, 0, {
                'hs_id':line.hs_id.id,
                'hs_en_name': line.hs_en_name,
                'back_tax':line.back_tax,
                'purchase_amount2_tax': line.purchase_amount2_tax,
                'purchase_amount2_no_tax': line.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast': line.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast': line.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest': line.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest': line.purchase_amount_min_add_rest,
                'hsname_all_line_id': line.id
            }))
        self.hsname_all_ids = res
        self.invoice_product_id = self.env.ref('yjzy_extend.product_qtyfk').id
    #
    # @api.onchange('hsname_all_ids')
    # def onchange_p_s_add_this_time(self):
    #     for one in self:
    #         p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
    #         purchase_invoice_amount = one.purchase_invoice_amount
    #         if purchase_invoice_amount - p_s_add_this_time_total > 0:
    #             p_s_add_this_time_refund = p_s_add_this_time_total
    #         else:
    #             p_s_add_this_time_refund = purchase_invoice_amount
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
    #     purchase_invoice_amount = sum(x.residual for x in purchase_invoice_partner_id)
    #     purchase_invoice_include_tax = purchase_invoice_partner_id and purchase_invoice_partner_id[0].include_tax or False
    #     print('purchase_invoice_amount', purchase_invoice_amount, purchase_invoice_partner_id,
    #           self.tb_id.purchase_invoice_ids)
    #     self.purchase_invoice_amount = purchase_invoice_amount
    #     self.purchase_invoice_include_tax = purchase_invoice_include_tax
    #     self.purchase_invoice_origin_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0] or False



    def apply(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        account = product.property_account_income_id
        account_domain = [('code', '=', '220299'), ('company_id', '=', self.env.user.company_id.id)]
        account_id = self.env['account.account'].search(account_domain, limit=1)
        if account_id == False:
            raise Warning('请先设置额外账单的科目')
        print('purchase_invoice_origin_id',self.purchase_invoice_origin_id)

        inv = invoice_obj.create({
            'tb_po_invoice_id':self.id,
            'partner_id': self.partner_id.id,
            'bill_id': self.tb_id.id,
            'invoice_attribute':'other_po',
            'type': 'in_invoice',
            'journal_type': 'purchase',
            'yjzy_type': 'purchase',
            'yjzy_payment_term_id':self.purchase_invoice_origin_id.payment_term_id.id,
            'yjzy_currency_id':self.purchase_invoice_origin_id.currency_id.id,
            # 'payment_term_id': self.purchase_invoice_origin_id.payment_term_id.id,
            # 'currency_id': self.purchase_invoice_origin_id.currency_id.id,
            'date':self.purchase_invoice_origin_id.date,
            'date_invoice':self.purchase_invoice_origin_id.date_invoice,
            'date_finish': self.purchase_invoice_origin_id.date_finish,
            'po_id':self.purchase_invoice_origin_id.po_id.id,
            'account_id':account_id.id,
            'invoice_line_ids': [(0, 0, {
                               'name': '%s' % (product.name),
                               'product_id': product.id,
                               'quantity': 1,
                               'price_unit': self.purchase_amount2_add_this_time_total,
                               'account_id': account.id,
            })]
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
        self.make_back_tax()
        self.make_sale_invoice()
        self.make_sale_invoice_extra()
        form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_po_form').id
        return {
            'name': u'增加采购额外账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views':[(form_view,'form')],
            'res_id':inv.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }
    def make_back_tax(self):
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        product = self.env.ref('yjzy_extend.product_back_tax')
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
                'yjzy_type': 'back_tax',
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
            # 730 创建后直接过账
    def make_sale_invoice(self):
        self.ensure_one()
        # self.check()
        invoice_obj = self.env['account.invoice']
        invoice_line_obj = self.env['account.invoice.line']
        hsname_all_line_obj = self.env['invoice.hs_name.all']
        purchase_orders = invoice_obj.browse()
        # product = self.env.ref('yjzy_extend.product_back_tax')
        product = self.invoice_product_id
        account = product.property_account_income_id
        if self.p_s_add_this_time_refund != 0:
            inv = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'type': 'in_refund',
                'journal_type': 'purchase',
                'yjzy_type': 'purchase',
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
        product = self.invoice_product_id
        account = product.property_account_income_id
        if self.p_s_add_this_time_extra_total != 0:
            inv = invoice_obj.create({
                'tb_po_invoice_id': self.id,
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute': 'other_po',
                'type': 'out_invoice',
                'journal_type': 'sale',
                'yjzy_type': 'sale',
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
        inv = invoice_obj.create({
                'partner_id': self.partner_id.id,
                'bill_id': self.tb_id.id,
                'invoice_attribute':'expense_po',
                'expense_sheet_id':self.expense_sheet_id.id,
                'type':'in_invoice',
                'journal_type':'purchase',
                'yjzy_type':'purchase',
                'invoice_line_ids': [(0, 0, {
                                   'name': '%s' % (product.name),
                                   'product_id': product.id,
                                   'quantity': 1,
                                   'price_unit': self.purchase_amount2_add_this_time_total,
                                   'account_id': account.id,
            })]
            })


        for line in self.hsname_all_ids:
            hsname_all_line = hsname_all_line_obj.create({
                'invoice_id': inv.id,
                'hs_id': line.hs_id.id,
                'hs_en_name':line.hs_en_name,
                'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
                'tbl_hsname_all_id':line.hsname_all_line_id.id
            })
        self.expense_sheet_id.invoice_id = inv
        form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_po_form').id
        return {
            'name': u'增加采购额外账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'account.invoice',
            'views':[(form_view,'form')],
            'res_id':inv.id,
            'type': 'ir.actions.act_window',
            'target': 'new',

        }




class tb_po_invoice_line(models.Model):
    _name = 'tb.po.invoice.line'




    tb_po_id = fields.Many2one('tb.po.invoice', 'TB_PO')
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
    p_s_add_this_time = fields.Float(u'本次应收金额')
    back_tax_add_this_time = fields.Float('本次应生成退税')
    p_s_add_this_time_old = fields.Float(u'冲减原始应付金额')
    yjzy_invoice_id = fields.Many2one('account.invoice',u'关联账单')

    hs_id = fields.Many2one('hs.hs', u'品名',related='hsname_all_line_id.hs_id')
    back_tax = fields.Float(u'退税率',related='hsname_all_line_id.back_tax')
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'),related='hsname_all_line_id.amount2')
    purchase_amount2_tax = fields.Float(u'含税采购金额',related='hsname_all_line_id.purchase_amount2_tax')
    purchase_amount2_no_tax = fields.Float(u'不含税采购金额',related='hsname_all_line_id.purchase_amount2_no_tax')
    purchase_back_tax_amount2_new = fields.Float(u'原始退税金额',related='hsname_all_line_id.purchase_back_tax_amount2_new')#根据是否含税来进行计算
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_min_add_forecast')
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_max_add_forecast')
    purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_max_add_rest')
    purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2),related='hsname_all_line_id.purchase_amount_min_add_rest')
    purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额',related='hsname_all_line_id.purchase_amount2_add_actual')
    @api.onchange('purchase_amount2_add_this_time')
    def onchange_purchase_amount2_add_this_time(self):
        for one in self:
            back_tax_add_this_time = one.purchase_amount2_add_this_time / 1.13 * one.back_tax
            one.back_tax_add_this_time = back_tax_add_this_time





    @api.constrains('qty', 'supplier_id')
    def check(self):
        if self.qty < 0:
            raise Warning(u'采购数量不能小于0')


#####################################################################################################################
