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

    # last_sale_price =  fields.Float('最后销售价格', compute='_compute_last_sale_price', digits=dp.get_precision('Product Price'))
    # last_purchase_price = fields.Float(u'最后采购价', compute='_compute_last_purchase_price', digits=dp.get_precision('Product Price'))
    #
    # # @api.multi
    # def _compute_last_purchase_price(self):



class sale_order(models.Model):
    _inherit = 'sale.order'




class sale_order_line(models.Model):
    _inherit = 'sale.order.line'
# _rec_name = 'percent'



