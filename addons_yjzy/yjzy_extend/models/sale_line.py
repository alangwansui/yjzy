# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO



class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
   # _rec_name = 'percent'


    @api.multi
    def _analytic_compute_delivered_quantity(self):
        res = super(sale_order_line, self)._analytic_compute_delivered_quantity()
        for one in self:
            if one.qty_delivered > one.product_uom_qty:
                raise Warning('发货数不能大于订单数量')
        return res

    def get_stock_cost(self):
        #结果返回为公司本币
        stock_cost = 0.0
        for x in self.smline_ids:
            po_currency = x.lot_id.pol_id.currency_id
            stock_cost += po_currency.compute(x.product_uom_qty * x.lot_id.purchase_price, self.company_currency_id)
        return stock_cost

    def get_purchase_cost(self):
        #结果返回为公司本币
        purchase_cost = fandian_amoun = 0.0
        for x in self.dlr_ids:
            po = x.po_id
            purchase_cost += x.purchase_currency_id.compute(x.purchase_amount, self.company_currency_id)
            fd = 0
            if po.need_purchase_fandian:
                fd = purchase_cost * po.purchase_fandian_ratio  / 100
                if self.include_tax:
                    fd =  fd /1.12
            fandian_amoun += fd
        return purchase_cost, fandian_amoun

    def compute_info(self):
        for one in self:
            #统计未发货

            #统计采购
            one.po_ids = one.pol_ids.mapped('order_id')
            one.pol_id = one.pol_ids and one.pol_ids[0] or False
            one.qty_unreceived = sum([x.product_qty - x.qty_received for x in one.pol_ids])

            #计算金额
            if one.order_id.company_id.is_current_date_rate:
                price_total2 = one.price_total * one.order_id.current_date_rate
            else:
                price_total2 = one.currency_id.compute(one.price_total, one.company_currency_id)

            purchase_cost, fandian_amoun = one.get_purchase_cost()
           # price_total_current_date_rate= one.price_total * one.order_id.current_date_rate
        #    print('====sdfdf===', gross_profit_ratio_line)
            stock_cost = one.get_stock_cost()
            #back_tax = one.order_id.cip_type != 'none' and one.product_id.back_tax or 0
            if one.order_id.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = (purchase_cost + stock_cost) / BACK_TAX_RATIO * one.back_tax  #固定0.16的税，退回0.05
            gross_profit_ratio_line = price_total2 != 0 and (
                        price_total2 + back_tax_amount - purchase_cost) / price_total2 * 100 / 5
            one.price_total2 = price_total2
            one.purchase_cost = purchase_cost
            one.fandian_amoun = fandian_amoun
            one.stock_cost = stock_cost
            one.profit_amount = price_total2 - purchase_cost - stock_cost - fandian_amoun
            one.back_tax_amount = back_tax_amount
            one.rest_tb_qty = one.product_qty - sum(one.tbl_ids.mapped('qty2stage_new'))
            one.gross_profit_ratio_line = round(gross_profit_ratio_line,2)
            one.gross_profit_line = price_total2-purchase_cost
            one.fee_inner = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_inner
            one.fee_rmb1 = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_rmb1
            one.fee_rmb2 = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_rmb2
            one.fee_outer = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_outer
            one.fee_export_insurance = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_export_insurance
            one.fee_other = one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_other
            print('==99999=',  one.order_id.amount_total and one.price_unit / one.order_id.amount_total * one.order_id.fee_inner)




    def compute_info_pol_id(self):
        for one in self:
            #统计未发货

            #统计采购

            one.pol_id = one.pol_ids and one.pol_ids[0] or False
            one.supplier_id = one.pol_ids and one.pol_ids[0].partner_id or False
          #  one.purchase_price = one.pol_id and one.pol_id.price_unit or False



    #currency_id ==销售货币
    customer_pi = fields.Char(u'客户订单号',related='order_id.customer_pi')
    order_state = fields.Selection([('draft', '草稿'),
                  ('cancel', '取消'),
                  ('refused', u'拒绝'),
                  ('submit', u'待责任人审核'),
                  ('sales_approve', u'待业务合规审核'),
                  ('manager_approval', u'待总经理特批'),
                  ('approve', u'审批完成待出运'),
                  ('sale', '开始出运'),
                  ('abnormal', u'异常核销'),
                  ('verifying', u'正常核销'),
                  ('verification', u'核销完成'),],u'订单审批状态',related="order_id.state")
    current_date_rate = fields.Float('成本测算汇率',related='order_id.current_date_rate')
    contract_date = fields.Date('客户确认日期',related='order_id.contract_date')
    product_so_line_count = fields.Integer(u'产品销售次数', related='product_id.so_line_count')
    #822
    contract_code = fields.Char('销售合同号',related='order_id.contract_code')
    #13添加

    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='order_id.company_currency_id', readonly=True)
    third_currency_id = fields.Many2one('res.currency', related='order_id.third_currency_id', readonly=True)
    include_tax = fields.Boolean(related='order_id.include_tax')
    pol_ids = fields.One2many('purchase.order.line', 'sol_id', u'采购明细', copy=False)
    po_ids = fields.Many2many('purchase.order', string=u'采购订单', compute=compute_info, store=False)
    purchase_qty_new = fields.Float(u'采购数', related='pol_id.product_qty')  # akiny 直接取对应的采购合同的数量而不是预留的数量
    qty_unreceived = fields.Float(u'未收数', compute=compute_info, store=False)



    tbl_ids = fields.One2many('transport.bill.line', 'sol_id', u'出运明细')  # 13已
    rest_tb_qty = fields.Float('出运剩余数', compute=compute_info)  # 13已 参与测试后期删除
    new_rest_tb_qty = fields.Float('新:出运剩余数', compute='compute_rest_tb_qty', store=True)  # 13已

    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))
    price_total2 = fields.Monetary(u'销售金额', currency_field='company_currency_id', compute=compute_info)  # 'sale_amount': sol.price_total,
    purchase_price_original = fields.Float(u'采购单价', related='pol_id.price_unit', digits=(2, 2))
    back_tax_amount = fields.Monetary(u'退税金额', currency_field='company_currency_id', compute=compute_info)
    profit_amount = fields.Monetary(u'利润', currency_field='company_currency_id', compute=compute_info)
    is_gold_sample = fields.Boolean('是否有金样', related='product_id.is_gold_sample', readonly=False)
    is_ps = fields.Boolean('是否有PS',related='product_id.is_ps', readonly=False)
    bom_id = fields.Many2one('mrp.bom', 'BOM')#13已
    bom_qty = fields.Float(u'BOM数量')#13已
    need_split_bom = fields.Boolean(u'需要展开BOM')#13已
    need_print = fields.Boolean('是否打印', default=True)#13已
    #-----
    last_sale_price = fields.Float('最后销售价', related='product_id.last_sale_price')

    purchase_qty = fields.Float(u'采购数', compute=compute_info, store=False)

    purchase_cost = fields.Monetary(u'采购成本', currency_field='company_currency_id', compute=compute_info)

    fandian_amoun = fields.Monetary(u'返点金额', currency_field='company_currency_id', compute=compute_info)
    stock_cost = fields.Monetary(u'库存成本', currency_field='company_currency_id', compute=compute_info)

    cost_amount = fields.Monetary(u'成本金额', currency_field='company_currency_id', compute=compute_info)

    purchase_payment_term = fields.Many2one('account.payment.term',u'供应商付款条款', related='pol_id.order_id.payment_term_id')

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位',)
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位',)




    second_unit_price = fields.Float('第二价格')
    second_price_total = fields.Monetary(compute='_compute_second', string='第二小计', readonly=True, store=True)

    hs_id = fields.Many2one('hs.hs', '报关品名', related='product_id.hs_id')
    hs_name = fields.Char('中文品名', related='product_id.hs_id.name')
    purchase_contract_code = fields.Char('采购合同', related='pol_id.order_id.contract_code')

    gross_profit_ratio_line = fields.Float(u'毛利润率', digits=(2, 2), compute=compute_info)
    gross_profit_line = fields.Float(u'毛利润', digits=(2, 2), compute=compute_info)
    #gross_profit_ratio_line_p = fields.Percent(u'毛利润率', digits=(2, 2), compute=compute_info)
    #vat_diff_amount = fields.Monetary(u'增值税差额', currency_field='company_currency_id')

    fee_inner = fields.Monetary(u'国内运杂费:单个', currency_field='company_currency_id',  compute=compute_info)
    fee_rmb1 = fields.Monetary(u'人民币费用1:单个', currency_field='company_currency_id', compute=compute_info)
    fee_rmb2 = fields.Monetary(u'人民币费用2:单个', currency_field='company_currency_id', compute=compute_info)
    fee_outer = fields.Monetary(u'国外运保费', currency_field='other_currency_id', compute=compute_info)
    fee_export_insurance = fields.Monetary(u'出口保险费:单个', currency_field='other_currency_id', compute=compute_info)
    fee_other = fields.Monetary(u'其他外币费用:单个', currency_field='other_currency_id', compute=compute_info)

    outer_currency_id = fields.Many2one('res.currency', u'国外运保费货币', related='order_id.outer_currency_id')
    export_insurance_currency_id = fields.Many2one('res.currency', u'出口保险费货币', related='order_id.export_insurance_currency_id')
    other_currency_id = fields.Many2one('res.currency', u'其他国外费用货币', related='order_id.other_currency_id')
    #14.0--------------------------
    @api.depends('tbl_ids','tbl_ids.state','tbl_ids.qty')
    def compute_project_tb_qty(self):
        for one in self:
            tbl_ids_undone = one.tbl_ids.filtered(lambda x: x.state in ['draft','submit','sale_approve','manager_approve','approve','refused'])
            project_tb_qty = sum(x.qty for x in tbl_ids_undone)
            can_project_tb_qty = one.product_uom_qty - project_tb_qty
            one.project_tb_qty = project_tb_qty
            one.can_project_tb_qty = can_project_tb_qty
    @api.depends('purchase_price','product_uom_qty')
    def compute_purchase_cost_new(self):
        for one in self:
            purchase_cost_new = one.purchase_price * one.product_uom_qty
            one.purchase_cost_new = purchase_cost_new

    # def compute_product_supplier_ref(self):
    #     for one in self:
    #         supplier_id = one.supplier_id
    #         product_id = one.product_id
    #         variant_seller_ids = product_id.variant_seller_ids.filtered(lambda x: x.name == supplier_id)
    #         if supplier_id and product_id:
    #             product_supplier_ref = variant_seller_ids.full_name
    #         else:
    #             product_supplier_ref = False
    #         one.product_supplier_ref = product_supplier_ref

    @api.depends('product_uom_qty','qty_delivered')
    def compute_qty_undelivered(self):
        for one in self:
            one.qty_undelivered = one.product_uom_qty - one.qty_delivered

    @api.depends('tbl_ids','tbl_ids.bill_id.state')
    def compute_tb_line_count(self):
        for one in self:
            one.tb_line_count = len(one.tbl_ids.filtered(lambda x: x.bill_id.state in ['delivered', 'invoiced', 'abnormal', 'verifying', 'done', 'paid']))

    qty_undelivered = fields.Float(string=u'未发货', readonly=True, compute=compute_qty_undelivered, store=True)
    project_tb_qty = fields.Float('已计划发货',compute='compute_project_tb_qty',store=True)
    can_project_tb_qty = fields.Float('可计划发货',compute='compute_project_tb_qty',store=True)
    # product_default_code = fields.Char('公司型号',related='product_id.default_code',store=True)
    # product_customer_ref = fields.Char('供应商型号',related='product_id.customer_ref',store=True)
    # product_supplier_ref = fields.Char('供应商信号',compute='compute_product_supplier_ref',store=True)

    purchase_price = fields.Float('采购价格', copy=False, digits=dp.get_precision('Product Price'), default = 0.0)
    purchase_cost_new = fields.Monetary(u'采购总价', currency_field='company_currency_id',
                                        compute='compute_purchase_cost_new', store=True)
    tb_line_count = fields.Integer('发货次数', compute=compute_tb_line_count)

    def open_bill_ids(self):
        tree_view_id = self.env.ref('yjzy_extend.view_transport_bill_tenyale_sales_tree').id
        return {
            'name': u'查看出运列表',
            'view_type': 'tree',
            'view_mode': 'tree',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id, 'tree')],
            'domain': [('bill_id', 'in', self.bill_id.id)],
            'target': 'new',
            'context': {
                        }
        }


    # ----------
    #m2m不可以随便加入depends
    @api.depends('tbl_ids','tbl_ids.plan_qty','tbl_ids.qty2stage_new','product_qty','order_id.state','price_unit')
    def compute_rest_tb_qty(self):
        for one in self:
            one.new_rest_tb_qty = one.product_qty - sum(one.tbl_ids.mapped('qty2stage_new'))


    def open_soline_form(self):
        view = self.env.ref('yjzy_extend.new_sale_order_line_from')
        return {
            'type': 'ir.actions.act_window',
            'name': u'销售明细',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [ (view.id, 'form')],
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
        }



    @api.depends('second_unit_price', 'discount', 'price_unit', 'tax_id')
    def _compute_second(self):
        """
        """
        for line in self:
            price = line.second_unit_price    #* (1 - (line.discount or 0.0) / 100.0)
            taxes = line.tax_id.compute_all(price, line.order_id.currency_id, line.product_uom_qty, product=line.product_id, partner=line.order_id.partner_shipping_id)
            line.update({
                'second_price_total': taxes['total_excluded'],
            })


    @api.multi
    @api.onchange('product_id')
    def product_id_change(self):
       # supplierinfo = self.env["product.supplierinfo"].search(
      #      [('product_id', '=', self.product_id.id), ('name', '=', self.supplier_id.id)], limit=1)
        res = super(sale_order_line, self).product_id_change()
        self.back_tax = self.product_id.back_tax
        #self.s_uom_id = self.product_id.uom_id
        #self.p_uom_id = self.product_id.uom_po_id
        self.s_uom_id = self.product_id.s_uom_id
        self.p_uom_id = self.product_id.p_uom_id
        self.need_split_bom = self.product_id.need_split_bom
        self.need_print = self.product_id.need_print
        self.supplier_id = self.product_id.variant_seller_ids and self.product_id.variant_seller_ids[0].name.is_ok == True and self.product_id.variant_seller_ids[0].name.id or None,
        return res

    def _prepare_invoice_line(self, qty):
        u'''开票数量根据发运单指定'''
        ctx = self.env.context
        manual_qty_dic = ctx.get('manual_qty_dic', {})
        if manual_qty_dic.get(self.id):
            manual_qty = manual_qty_dic.get(self.id)
            # if manual_qty > qty:
            #     raise Warning(u'手动开票数量已经超过剩余开票数量')
            # else:
            qty = manual_qty
        return super(sale_order_line, self)._prepare_invoice_line(qty)

    def get_in_stock_quant(self):
        self.ensure_one()
        return self.product_id.get_in_stock_quant()


    def show_product_attrs(self):
        values = self.product_id.attribute_value_ids
        return {
            'type': 'ir.actions.act_window',
            'name': u'产品属性',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'product.attribute.value',
            'domain': [('id', 'in', [x.id for x in values])],
            'target': 'new',
        }

