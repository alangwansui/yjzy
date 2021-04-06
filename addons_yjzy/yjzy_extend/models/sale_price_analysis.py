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
            line_ids = one.order_line.filtered(lambda x: x.price_unit != x.product_last_price or x.purchase_price != x.product_purchase_last_price)
            one.order_line_analysis = line_ids


    def compute_lens(self):
        for one in self:
            order_line_analysis= one.order_line_analysis
            one.higher_last_sale_price = len(order_line_analysis.filtered(lambda x: x.price_unit > x.product_last_price ))
            one.lower_last_sale_price = len(order_line_analysis.filtered(lambda x: x.price_unit < x.product_last_price))
            one.higher_last_purchase_price = len(order_line_analysis.filtered(lambda x: x.purchase_price > x.product_purchase_last_price))
            one.lower_last_purchase_price = len(order_line_analysis.filtered(lambda x: x.purchase_price < x.product_purchase_last_price))


    order_line_analysis = fields.Many2many('sale.order.line','价格分析明细', 'order_line_id', 'sid', 'oid',compute='compute_order_line_analysis')


    higher_last_sale_price = fields.Integer('售价高于上次数',compute=compute_lens)
    lower_last_sale_price = fields.Integer('售价低于上次数', compute=compute_lens)
    higher_last_purchase_price = fields.Integer('成本高于上次数',compute=compute_lens)
    lower_last_purchase_price = fields.Integer('成本低于上次数',compute=compute_lens)

class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
# _rec_name = 'percent'

    @api.depends('hegui_date','order_id','order_id.state_1')
    def compute_today_hegui_date(self):
        strptime = datetime.strptime
        for one in self:

            if one.hegui_date:
                today_hegui_date = ((datetime.today() - relativedelta(hours=-8)) - strptime(one.hegui_date, DF)).days
            else:
                today_hegui_date = -999
            print('today_hegui_akiny',today_hegui_date)
            one.today_hegui_date = today_hegui_date

    @api.depends('price_unit','purchase_price','product_id','order_id','order_id.state_1')
    def compute_product_last_price(self):
        so_line_obj = self.env['sale.order.line']
        for one in self:
            so_line = so_line_obj.search([('today_hegui_date', '>', 0), ('product_id', '=', one.product_id.id),('order_partner_id','=',one.order_partner_id.id)],order='today_hegui_date,id desc' , limit=1)
            if so_line:
                product_last_price = so_line.price_unit
                product_purchase_last_price = so_line.purchase_price
            else:
                product_last_price = 0
                product_purchase_last_price = 0

            one.product_last_price = product_last_price
            one.product_purchase_last_price = product_purchase_last_price

    @api.depends('price_unit','purchase_price','order_id','order_id.state_1')
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
    product_last_price = fields.Float('最近一次销售价格', compute='compute_product_last_price',digits=dp.get_precision('Product Price'),store=True)

    product_purchase_last_price = fields.Float('最近一次采购价格', compute='compute_product_last_price',digits=dp.get_precision('Product Price'),store=True)

    @api.depends('price_unit','purchase_price','order_id.state_1','product_purchase_last_price','product_last_price')
    def compute_price_change_percent(self):
        for one in self:
            price_unit = one.price_unit
            product_last_price = one.product_last_price

            purchase_price = one.purchase_price
            product_purchase_last_price = one.product_purchase_last_price

            sale_price_change_percent = product_last_price and (price_unit - product_last_price) * 100 / product_last_price or 0.0
            purchase_price_change_percent = product_purchase_last_price and (purchase_price - product_purchase_last_price) * 100 / product_purchase_last_price or 0.0
            if sale_price_change_percent >= 0:
                is_change = True
            else:
                is_change = False

            one.sale_price_change_percent = sale_price_change_percent
            one.purchase_price_change_percent = purchase_price_change_percent
            one.is_change = is_change

    def compute_price_percent(self):
        for one in self:
            highest_price = one.highest_price
            lowest_price = one.lowest_price
            price_unit = one.price_unit
            sale_price_percent =highest_price - lowest_price !=0 and  (price_unit - lowest_price) * 100 / (highest_price - lowest_price) or 0.0

            purchase_highest_price = one.purchase_highest_price
            purchase_lowest_price = one.purchase_lowest_price
            purchase_price = one.purchase_price
            purchase_price_percent = purchase_highest_price - purchase_lowest_price != 0 and (purchase_price - purchase_lowest_price) * 100 / (
                        purchase_highest_price - purchase_lowest_price) or 0.0

            one.sale_price_percent = sale_price_percent
            one.purchase_price_percent = purchase_price_percent

    sale_price_change_percent = fields.Float('变动比率',  digits=(2, 2),compute=compute_price_change_percent,store=True)
    is_change = fields.Boolean('变动方向',compute=compute_price_change_percent,store=True)
    purchase_price_change_percent = fields.Float('变动比率',  digits=(2, 2),compute=compute_price_change_percent, store=True)

    sale_price_percent = fields.Float('本次在历史价格区间的位置',compute=compute_price_percent)
    purchase_price_percent = fields.Float('本次在历史价格区间的位置', compute=compute_price_percent)

    average_price = fields.Float('历史平均价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    highest_price = fields.Float('历史最高价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    lowest_price = fields.Float('历史最低价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_average_price = fields.Float('采购历史平均价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_highest_price = fields.Float('采购历史最高价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)
    purchase_lowest_price = fields.Float('采购历史最低价', compute='compute_product_other_price',digits=dp.get_precision('Product Price'),store=True)

