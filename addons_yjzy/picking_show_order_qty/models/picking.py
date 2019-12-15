# -*- coding: utf-8 -*-

from odoo import models, fields, api

class stock_move_ordered_qty(models.Model):
    _inherit = 'stock.move'

    so_qty = fields.Float(related='sale_line_id.product_uom_qty', string=u'销售数量', readonly=True)





