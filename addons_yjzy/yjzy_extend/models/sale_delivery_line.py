# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp

from odoo.exceptions import Warning
from .comm import BACK_TAX_RATIO
from datetime import datetime
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class sale_order(models.Model):
    _inherit = 'sale.order'

    @api.depends('order_line')
    def compute_delivery_line_ids(self):
        for one in self:
            one.delivery_line_ids = one.order_line

    delivery_line_ids = fields.Many2many('sale.order.line','sdid','olid','qid',u'销售明细数量数据',compute=compute_delivery_line_ids)