# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from datetime import datetime
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO



class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

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
            one.qty_undelivered = one.product_uom_qty - one.qty_delivered
            #统计采购
            one.po_ids = one.pol_ids.mapped('order_id')
            one.pol_id = one.pol_ids and one.pol_ids[0] or False
            one.qty_unreceived = sum([x.product_qty - x.qty_received for x in one.pol_ids])
            one.qty_undelivered = one.product_uom_qty - one.qty_delivered
            #计算金额
            price_total2 = one.currency_id.compute(one.price_total, one.company_currency_id)
            purchase_cost, fandian_amoun = one.get_purchase_cost()

            stock_cost = one.get_stock_cost()
            #back_tax = one.order_id.cip_type != 'none' and one.product_id.back_tax or 0

            if one.order_id.cip_type != 'normal':
                back_tax_amount = 0
            else:
                back_tax_amount = (purchase_cost + stock_cost) / BACK_TAX_RATIO * one.back_tax  #固定0.16的税，退回0.05

            one.price_total2 = price_total2
            one.purchase_cost = purchase_cost
            one.fandian_amoun = fandian_amoun
            one.stock_cost = stock_cost
            one.profit_amount = price_total2 - purchase_cost - stock_cost - fandian_amoun
            one.back_tax_amount = back_tax_amount
            one.rest_tb_qty = one.product_qty - sum(one.tbl_ids.mapped('qty2stage'))

    #currency_id ==销售货币
    sale_currency_id = fields.Many2one('res.currency', related='currency_id', string=u'交易货币', readonly=True)
    company_currency_id = fields.Many2one('res.currency', related='order_id.company_currency_id', readonly=True)
    third_currency_id = fields.Many2one('res.currency', related='order_id.third_currency_id', readonly=True)
    include_tax = fields.Boolean(related='order_id.include_tax')

    last_sale_price = fields.Float('最后销售价', related='product_id.last_sale_price')
    pol_ids = fields.One2many('purchase.order.line', 'sol_id', u'采购明细', copy=False)
    po_ids = fields.Many2many('purchase.order', string=u'采购订单', compute=compute_info, store=False)
    purchase_qty = fields.Float(u'采购数', compute=compute_info, store=False)
    qty_unreceived = fields.Float(u'未收数', compute=compute_info, store=False)
    qty_undelivered = fields.Float(string=u'未发货', readonly=True, store=False, compute=compute_info)
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    price_total2 = fields.Monetary(u'销售金额', currency_field='company_currency_id', compute=compute_info)  # 'sale_amount': sol.price_total,
    purchase_cost = fields.Monetary(u'采购成本', currency_field='company_currency_id', compute=compute_info)
    fandian_amoun = fields.Monetary(u'返点金额', currency_field='company_currency_id', compute=compute_info)
    stock_cost = fields.Monetary(u'库存成本', currency_field='company_currency_id', compute=compute_info)
    back_tax_amount = fields.Monetary(u'退税金额', currency_field='company_currency_id', compute=compute_info)
    cost_amount = fields.Monetary(u'成本金额', currency_field='company_currency_id', compute=compute_info)
    profit_amount = fields.Monetary(u'利润', currency_field='company_currency_id', compute=compute_info)
    bom_id = fields.Many2one('mrp.bom', 'BOM')
    bom_qty = fields.Float(u'BOM数量')
    need_split_bom = fields.Boolean(u'需要展开BOM')
    need_print = fields.Boolean('是否打印', defualt=True)

    s_uom_id = fields.Many2one('product.uom', u'销售打印单位',)
    p_uom_id = fields.Many2one('product.uom', u'采购打印单位',)
    tbl_ids = fields.One2many('transport.bill.line', 'sol_id', u'出运明细')
    rest_tb_qty = fields.Float('出运剩余数', compute=compute_info)

    second_unit_price = fields.Float('第二价格')
    second_price_total = fields.Monetary(compute='_compute_second', string='第二小计', readonly=True, store=True)
    is_gold_sample = fields.Boolean('是否有金样', related='product_id.is_gold_sample', readonly=False)
    hs_id = fields.Many2one('hs.hs', '报关品名', related='product_id.hs_id')

    purchase_contract_code = fields.Char('采购合同', related='po_id.contract_code')


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
        res = super(sale_order_line, self).product_id_change()
        self.back_tax = self.product_id.back_tax
        self.s_uom_id = self.product_id.uom_id
        self.p_uom_id = self.product_id.uom_po_id
        self.need_split_bom = self.product_id.need_split_bom
        self.need_print = self.product_id.need_print
        return res

    def _prepare_invoice_line(self, qty):
        u'''开票数量根据发运单指定'''
        ctx = self.env.context
        manual_qty_dic = ctx.get('manual_qty_dic', {})
        if manual_qty_dic.get(self.id):
            manual_qty = manual_qty_dic.get(self.id)
            if manual_qty > qty:
                raise Warning(u'手动开票数量已经超过剩余开票数量')
            else:
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

