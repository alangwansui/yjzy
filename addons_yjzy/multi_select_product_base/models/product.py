# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.exceptions import Warning

class product_product(models.Model):
    _inherit = 'product.product'

    add_qty = fields.Float(u'Line Qty', default=0, store=False)
    add_price = fields.Float(u'价格', default=0, store=False)

    def add_line_to_main_order(self):
        #hooks to add main_order line
        self.ensure_one()
        self.add_qty = 1

    @api.onchange('add_qty')
    def onchange_add_qty(self):
        print('==onchange_add_qty===', self.add_qty, self.env.context)
        return {}











