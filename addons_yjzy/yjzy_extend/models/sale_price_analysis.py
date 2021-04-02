# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

from odoo.exceptions import Warning
from .comm import BACK_TAX_RATIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF



class ProductProduct(models.Model):
    _inherit = "product.product"


class sale_order(models.Model):
    _inherit = 'sale.order'


    def compute_order_line_analysis(self):
        for one in self:
            line_ids = one.order_line.filtered(lambda x: x.price_unit != x.product_last_price)
            one.order_line_analysis = line_ids

    order_line_analysis = fields.Many2many('sale.order.line','价格分析明细', 'order_line_id', 'sid', 'oid',compute='compute_order_line_analysis')

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
# _rec_name = 'percent'

    @api.depends('hegui_date')
    def compute_today_hegui_date(self):
        strptime = datetime.strptime
        for one in self:

            if one.hegui_date:
                today_hegui_date = ((datetime.today() - relativedelta(hours=-8)) - strptime(one.hegui_date, DF)).days
            else:
                today_hegui_date = -999
            print('today_hegui_akiny',today_hegui_date)
            one.today_hegui_date = today_hegui_date

    @api.depends('price_unit','purchase_price','product_id')
    def compute_product_last_price(self):
        so_line_obj = self.env['sale.order.line']
        for one in self:
            so_line = so_line_obj.search([('today_hegui_date', '>', 0), ('product_id', '=', one.product_id.id),('order_partner_id','=',one.order_partner_id.id)],order='today_hegui_date,id' , limit=1)
            if so_line:
                product_last_price = so_line.price_unit
                product_purchase_last_price = so_line.purchase_price
            else:
                product_last_price = 0
                product_purchase_last_price = 0

            one.product_last_price = product_last_price
            one.product_purchase_last_price = product_purchase_last_price

    @api.depends('price_unit','purchase_price')
    def compute_product_other_price(self):
        so_line_obj = self.env['sale.order.line']
        for one in self:
            so_line = so_line_obj.search([('product_id', '=', one.product_id.id),('order_partner_id','=',one.order_partner_id.id)])
            price_amount_so_line = sum(line.price_unit for line in so_line)
            len_so_line =len(so_line)
            average_price = len_so_line != 0 and price_amount_so_line / len_so_line
            price_dic = []
            for price in so_line:
                price_dic.append(price.price_unit)
            highest_price = max(price_dic)
            lowest_price = min(price_dic)

            purchase_price_amount_so_line = sum(line.purchase_price for line in so_line)
            len_so_line = len(so_line)
            purchase_average_price = len_so_line != 0 and purchase_price_amount_so_line / len_so_line
            purchase_price_dic = []
            for purchase_price in so_line:
                purchase_price_dic.append(purchase_price.purchase_price)
            purchase_highest_price = max(purchase_price_dic)
            purchase_lowest_price = min(purchase_price_dic)

            print('other_price_akiny', so_line, price_amount_so_line, len_so_line, average_price, price_dic,highest_price,lowest_price)
            one.average_price = average_price
            one.highest_price = highest_price
            one.lowest_price = lowest_price
            one.purchase_average_price = purchase_average_price
            one.purchase_highest_price = purchase_highest_price
            one.purchase_lowest_price = purchase_lowest_price





    hegui_date = fields.Date('合规审批时间',related='order_id.approve_date',store=True)
    today_hegui_date = fields.Integer('合规审批距离今天的日期',compute=compute_today_hegui_date,store=True)
    product_last_price = fields.Monetary('最近一次销售价格', compute='compute_product_last_price',digits=dp.get_precision('Product Price'),store=True)

    product_purchase_last_price = fields.Monetary('最近一次采购价格', compute='compute_product_last_price',digits=dp.get_precision('Product Price'),store=True)
    average_price = fields.Monetary('历史平均价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    highest_price = fields.Monetary('历史最高价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    lowest_price = fields.Monetary('历史最低价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_average_price = fields.Monetary('采购历史平均价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_highest_price = fields.Monetary('采购历史最高价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_lowest_price = fields.Monetary('采购历史最低价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)

