# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp


class wizard_transport4so(models.TransientModel):
    _name = 'wizard.tb.po.invoice'

    @api.depends('hsname_all_ids','hsname_all_ids.purchase_amount2_add_this_time','hsname_all_ids.p_s_add_this_time','partner_id')
    def compute_info(self):
        for one in self:
            purchase_amount2_add_this_time_total = sum(x.purchase_amount2_add_this_time for x in one.hsname_all_ids)
            p_s_add_this_time_total = sum(x.p_s_add_this_time for x in one.hsname_all_ids)
            back_tax_add_this_time_total = sum(x.back_tax_add_this_time for x in one.hsname_all_ids)
            purchase_invoice_partner_id = one.tb_id.purchase_invoice_ids.filtered(
                lambda x: x.partner_id == one.partner_id)
            # if len(purchase_invoice_partner_id) != 0:
            yjzy_invoice_residual_amount = sum(x.residual for x in purchase_invoice_partner_id)
            yjzy_invoice_include_tax = purchase_invoice_partner_id and purchase_invoice_partner_id[
                0].include_tax or False
            p_s_add_this_time_refund = 0.0
            if not yjzy_invoice_include_tax:
                if yjzy_invoice_residual_amount - p_s_add_this_time_total > 0 :
                    p_s_add_this_time_refund = p_s_add_this_time_total
                else:
                    p_s_add_this_time_refund = yjzy_invoice_residual_amount
            p_s_add_this_time_extra_total = p_s_add_this_time_total - p_s_add_this_time_refund
            one.p_s_add_this_time_extra_total = p_s_add_this_time_extra_total
            one.p_s_add_this_time_refund = p_s_add_this_time_refund
            one.purchase_amount2_add_this_time_total = purchase_amount2_add_this_time_total
            one.p_s_add_this_time_total = p_s_add_this_time_total
            one.back_tax_add_this_time_total = back_tax_add_this_time_total


            one.yjzy_invoice_residual_amount = yjzy_invoice_residual_amount
            one.yjzy_invoice_include_tax = yjzy_invoice_include_tax
            one.yjzy_invoice_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0] or False
            one.currency_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0].currency_id or self.env.user.company_id.currency_id.id


    # invoice_ids = fields.Many2many('account.invoice','ref_invoice_tb','invoice_id','tbl_id',u'额外账单')
    # hsname_id = fields.Many2one('tbl.hsname', u'报关明细')
    type = fields.Selection([('other_po', '直接增加'), ('expense_po', '费用转换')], u'类型')
    tb_id = fields.Many2one('transport.bill', u'出运单')
    partner_id = fields.Many2one('res.partner',u'合作伙伴')
    hsname_all_ids = fields.One2many('wizard.tb.po.invoice.line','wizard_id',u'报关明细')
    yjzy_invoice_id = fields.Many2one('account.invoice', '原始应付发票',compute=compute_info)
    currency_id = fields.Many2one('res.currency',compute=compute_info)
    purchase_amount2_add_this_time_total = fields.Float('本次增加采购金额',compute=compute_info)
    p_s_add_this_time_total = fields.Float('本次应收总金额',compute=compute_info)
    p_s_add_this_time_extra_total = fields.Float('本次额外应收金额', compute=compute_info)
    back_tax_add_this_time_total = fields.Float('本次退税金额', compute=compute_info)
    p_s_add_this_time_refund = fields.Float('本次冲减金额',compute=compute_info)
    invoice_product_id = fields.Many2one('product.product',u'账单项目')

    expense_sheet_id = fields.Many2one('hr.expense.sheet',u'费用报告')
    expense_currency_id = fields.Many2one('res.currency',related='expense_sheet_id.currency_id')
    expense_sheet_amount = fields.Float('费用报告金额', related='expense_sheet_id.total_amount')
    expense_po_amount = fields.Float('费用转应付金额',)

    yjzy_invoice_residual_amount = fields.Float('原始未付总金额', compute=compute_info)
    yjzy_invoice_include_tax = fields.Boolean('原始采购是否含税', compute=compute_info)

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

    # @api.onchange('partner_id')
    # def onchange_partner_id(self):
    #     purchase_invoice_partner_id = self.tb_id.purchase_invoice_ids.filtered(
    #         lambda x: x.partner_id == self.partner_id)
    #     print('purchase_invoice_partner_id', purchase_invoice_partner_id)
    #     # if len(purchase_invoice_partner_id) != 0:
    #     yjzy_invoice_residual_amount = sum(x.residual for x in purchase_invoice_partner_id)
    #     yjzy_invoice_include_tax = purchase_invoice_partner_id and purchase_invoice_partner_id[
    #         0].include_tax or False
    #     print('yjzy_invoice_residual_amount', yjzy_invoice_residual_amount, purchase_invoice_partner_id,
    #           self.tb_id.purchase_invoice_ids)
    #     self.yjzy_invoice_residual_amount = yjzy_invoice_residual_amount
    #     self.yjzy_invoice_include_tax = yjzy_invoice_include_tax
    #     self.yjzy_invoice_id = purchase_invoice_partner_id and purchase_invoice_partner_id[0] or False

    def apply_new(self):
        self.ensure_one()
        # self.check()
        tb_po_obj = self.env['tb.po.invoice']
        tb_po_line_obj = self.env['tb.po.invoice.line']
        tb_po = tb_po_obj.create({
            'partner_id': self.partner_id.id,
            'bill_id': self.tb_id.id,
            'purchase_amount2_add_this_time_total':self.purchase_amount2_add_this_time_total,
            'p_s_add_this_time_total':self.p_s_add_this_time_total,
            'p_s_add_this_time_extra_total':self.p_s_add_this_time_extra_total,
            'p_s_add_this_time_refund':self.p_s_add_this_time_refund,
            'invoice_product_id':self.invoice_product_id.id,
            'expense_sheet_id':self.expense_sheet_id.id,
            'expense_currency_id':self.expense_currency_id,
            #'expense_po_amount':self.expense_po_amount,
            'expense_sheet_amount':self.expense_sheet_amount,
            'yjzy_invoice_residual_amount':self.yjzy_invoice_residual_amount,
            'yjzy_invoice_include_tax':self.yjzy_invoice_include_tax,
            'type':self.type
        })
        for line in self.hsname_all_ids:
            tb_po_line= tb_po_line_obj.create({
                'tb_po_id': tb_po.id,
                'hs_id': line.hs_id.id,
                'hs_en_name': line.hs_en_name,
                'purchase_amount2_tax': line.purchase_amount2_tax,
                'purchase_amount2_no_tax': line.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast': line.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast': line.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest': line.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest': line.purchase_amount_min_add_rest,
                'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
                'p_s_add_this_time': line.p_s_add_this_time,
                'back_tax_add_this_time': line.back_tax_add_this_time,
                'hsname_all_line_id': line.hsname_all_line_id.id
            })

        form_view = self.env.ref('yjzy_extend.tb_po_form').id
        return {
            'name': u'增加采购额外账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'tb.po.invoice',
            'views': [(form_view, 'form')],
            'res_id': tb_po.id,
            'type': 'ir.actions.act_window',
            'target': 'current',

        }



    # def apply(self):
    #     self.ensure_one()
    #     # self.check()
    #     invoice_obj = self.env['account.invoice']
    #     invoice_line_obj = self.env['account.invoice.line']
    #     hsname_all_line_obj = self.env['invoice.hs_name.all']
    #     purchase_orders = invoice_obj.browse()
    #     # product = self.env.ref('yjzy_extend.product_back_tax')
    #     product = self.invoice_product_id
    #     account = product.property_account_income_id
    #     inv = invoice_obj.create({
    #             'partner_id': self.partner_id.id,
    #             'bill_id': self.tb_id.id,
    #             'invoice_attribute':'other_po',
    #             'type': 'in_invoice',
    #             'journal_type': 'purchase',
    #             'yjzy_type': 'purchase',
    #             'invoice_line_ids': [(0, 0, {
    #                                'name': '%s' % (product.name),
    #                                'product_id': product.id,
    #                                'quantity': 1,
    #                                'price_unit': self.purchase_amount2_add_this_time_total,
    #                                'account_id': account.id,
    #         })]
    #         })
    #     for line in self.hsname_all_ids:
    #         hsname_all_line = hsname_all_line_obj.create({
    #             'invoice_id': inv.id,
    #             'hs_id': line.hs_id.id,
    #             'hs_en_name':line.hs_en_name,
    #             'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
    #             'p_s_add_this_time':line.p_s_add_this_time,
    #             'back_tax_add_this_time':line.back_tax_add_this_time,
    #             'tbl_hsname_all_id':line.hsname_all_line_id.id
    #         })
    #     self.make_back_tax()
    #     self.make_sale_invoice()
    #     form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_po_form').id
    #     return {
    #         'name': u'增加采购额外账单',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'account.invoice',
    #         'views':[(form_view,'form')],
    #         'res_id':inv.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #
    #     }
    # def make_back_tax(self):
    #     partner = self.env.ref('yjzy_extend.partner_back_tax')
    #     product = self.env.ref('yjzy_extend.product_back_tax')
    #     # account = self.env['account.account'].search([('code','=', '50011'),('company_id', '=', self.user_id.company_id.id)], limit=1)
    #     account = product.property_account_income_id
    #
    #     invoice_obj = self.env['account.invoice']
    #     invoice_line_obj = self.env['account.invoice.line']
    #     hsname_all_line_obj = self.env['invoice.hs_name.all']
    #     if not account:
    #         raise Warning(u'没有找到退税科目,请先在退税产品的收入科目上设置')
    #     if self.back_tax_add_this_time_total != 0:
    #         back_tax_invoice = invoice_obj.create({
    #             'partner_id': partner.id,
    #             'type': 'out_invoice',
    #             'journal_type': 'sale',
    #             'bill_id': self.tb_id.id,
    #             'invoice_attribute': 'other_po',
    #             'yjzy_type': 'back_tax',
    #             'invoice_line_ids': [(0, 0, {
    #                 'name': '%s' % (product.name,),
    #                 'product_id': product.id,
    #                 'quantity': 1,
    #                 'price_unit': self.back_tax_add_this_time_total,
    #                 'account_id': account.id,
    #             })]
    #         })
    #         for line in self.hsname_all_ids:
    #             hsname_all_line = hsname_all_line_obj.create({
    #                 'invoice_id': back_tax_invoice.id,
    #                 'hs_id': line.hs_id.id,
    #                 'hs_en_name': line.hs_en_name,
    #                 'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
    #                 'p_s_add_this_time': line.p_s_add_this_time,
    #                 'back_tax_add_this_time': line.back_tax_add_this_time,
    #                 'tbl_hsname_all_id': line.hsname_all_line_id.id
    #                 })
    #         # 730 创建后直接过账
    # def make_sale_invoice(self):
    #     self.ensure_one()
    #     # self.check()
    #     invoice_obj = self.env['account.invoice']
    #     invoice_line_obj = self.env['account.invoice.line']
    #     hsname_all_line_obj = self.env['invoice.hs_name.all']
    #     purchase_orders = invoice_obj.browse()
    #     # product = self.env.ref('yjzy_extend.product_back_tax')
    #     product = self.invoice_product_id
    #     account = product.property_account_income_id
    #     if self.p_s_add_this_time_total != 0:
    #         inv = invoice_obj.create({
    #             'partner_id': self.partner_id.id,
    #             'bill_id': self.tb_id.id,
    #             'invoice_attribute': 'other_po',
    #             'type': 'out_invoice',
    #             'journal_type': 'sale',
    #             'yjzy_type': 'sale',
    #             'invoice_line_ids': [(0, 0, {
    #                 'name': '%s' % (product.name),
    #                 'product_id': product.id,
    #                 'quantity': 1,
    #                 'price_unit': self.p_s_add_this_time_total,
    #                 'account_id': account.id,
    #             })]
    #         })
    #         for line in self.hsname_all_ids:
    #             hsname_all_line = hsname_all_line_obj.create({
    #                 'invoice_id': inv.id,
    #                 'hs_id': line.hs_id.id,
    #                 'hs_en_name': line.hs_en_name,
    #                 'purchase_amount2_add_this_time': line.purchase_amount2_add_this_time,
    #                 'p_s_add_this_time': line.p_s_add_this_time,
    #                 'back_tax_add_this_time': line.back_tax_add_this_time,
    #                 'tbl_hsname_all_id': line.hsname_all_line_id.id
    #             })
    #
    #
    # def apply_expense_sheet(self):
    #     self.ensure_one()
    #     # self.check()
    #     invoice_obj = self.env['account.invoice']
    #     invoice_line_obj = self.env['account.invoice.line']
    #     hsname_all_line_obj = self.env['invoice.hs_name.all']
    #     purchase_orders = invoice_obj.browse()
    #     # product = self.env.ref('yjzy_extend.product_back_tax')
    #     product = self.invoice_product_id
    #     account = product.property_account_income_id
    #     inv = invoice_obj.create({
    #             'partner_id': self.partner_id.id,
    #             'bill_id': self.tb_id.id,
    #             'invoice_attribute':'expense_po',
    #             'expense_sheet_id':self.expense_sheet_id.id,
    #             'type':'in_invoice',
    #             'journal_type':'purchase',
    #             'yjzy_type':'purchase',
    #             'invoice_line_ids': [(0, 0, {
    #                                'name': '%s' % (product.name),
    #                                'product_id': product.id,
    #                                'quantity': 1,
    #                                'price_unit': self.purchase_amount2_add_this_time_total,
    #                                'account_id': account.id,
    #         })]
    #         })
    #
    #
    #     for line in self.hsname_all_ids:
    #         hsname_all_line = hsname_all_line_obj.create({
    #             'invoice_id': inv.id,
    #             'hs_id': line.hs_id.id,
    #             'hs_en_name':line.hs_en_name,
    #             'purchase_amount2_add_this_time':line.purchase_amount2_add_this_time,
    #             'tbl_hsname_all_id':line.hsname_all_line_id.id
    #         })
    #     self.expense_sheet_id.invoice_id = inv
    #     form_view = self.env.ref('yjzy_extend.view_supplier_invoice_extra_po_form').id
    #     return {
    #         'name': u'增加采购额外账单',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'account.invoice',
    #         'views':[(form_view,'form')],
    #         'res_id':inv.id,
    #         'type': 'ir.actions.act_window',
    #         'target': 'new',
    #
    #     }




class wizard_so2po_line(models.TransientModel):
    _name = 'wizard.tb.po.invoice.line'




    wizard_id = fields.Many2one('wizard.tb.po.invoice', 'Wizard')
    hsname_all_line_id = fields.Many2one('tbl.hsname.all', u'销售明细')
    hs_id = fields.Many2one('hs.hs', u'品名')


    hs_en_name = fields.Char(related='hs_id.en_name')


    hs_id2 = fields.Many2one('hs.hs', u'报关品名')
    out_qty2 = fields.Float('报关数量')
    price2 = fields.Float('报关价格', )


    suppliser_hs_amount = fields.Float('采购HS统计金额')

    # 销售hs统计同步采购hs统计
    purchase_amount2 = fields.Float('采购金额')  # 814需要优化

    # back_tax = fields.Float(u'退税率')
    # purchase_back_tax_amount2 = fields.Float(u'报关退税税金额', )
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

    back_tax = fields.Float(u'退税率')
    amount2 = fields.Float('报关金额', digits=dp.get_precision('Money'), related='hsname_all_line_id.amount2')
    purchase_amount2_tax = fields.Float(u'含税采购金额', related='hsname_all_line_id.purchase_amount2_tax')
    purchase_amount2_no_tax = fields.Float(u'不含税采购金额', related='hsname_all_line_id.purchase_amount2_no_tax')
    purchase_back_tax_amount2 = fields.Float(u'报关退税税金额', related='hsname_all_line_id.purchase_back_tax_amount2')
    purchase_amount_min_add_forecast = fields.Float('可增加采购额(上限)', digits=(2, 2),
                                                    related='hsname_all_line_id.purchase_amount_min_add_forecast')
    purchase_amount_max_add_forecast = fields.Float('可增加采购额(下限)', digits=(2, 2),
                                                    related='hsname_all_line_id.purchase_amount_max_add_forecast')
    purchase_amount_max_add_rest = fields.Float('采购池(下限)', digits=(2, 2),
                                                related='hsname_all_line_id.purchase_amount_max_add_rest')
    purchase_amount_min_add_rest = fields.Float('采购池(上限)', digits=(2, 2),
                                                related='hsname_all_line_id.purchase_amount_min_add_rest')
    purchase_amount2_add_actual = fields.Float(U'实际已经增加采购额', related='hsname_all_line_id.purchase_amount2_add_actual')

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
