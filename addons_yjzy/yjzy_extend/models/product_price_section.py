# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class product_price_section(models.Model):
    _name = 'product.price.section'

    def compute_name(self):
        for one in self:
            one.name = '%s~%s' % (one.start, one.end)

    name = fields.Char('区间', compute=compute_name)
    product_id = fields.Many2one('product.product', '产品')
    start = fields.Integer('开始')
    end = fields.Integer('结束')
    price = fields.Float('价格')

    @api.constrains('start', 'end')
    def check_star_end(self):
        for one in self:
            if one.start >= one.end:
                raise Warning('开始不能大于结束')
