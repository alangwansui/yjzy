# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class mrp_bom_line(models.Model):
    _inherit = 'mrp.bom.line'

    #template_id = fields.Many2one('product.template', u'模板')
    product_id = fields.Many2one('product.product', 'Product', required=True)
    price_percent = fields.Float(u'价格百分比',  digits=(6, 4),  store=True, help='物料在整个bom的价格中百分占比')

    def compute_price_percent(self):
        for one in self:
            bom_product = one.bom_id.product_id or one.bom_id.product_tmpl_id.product_variant_ids[0]
            bom_price = bom_product.lst_price
            total = one.product_qty * one.product_id.lst_price
            one.price_percent = bom_price and (total / bom_price) or 0

    # @api.onchange('template_id')
    # def onchange_tmpl(self):
    #     if self.product_tmpl_id:
    #         return {'domain': {'product_id': [('product_tmpl_id', '=', self.template_id.id)]}}
    #     else:
    #         return {'domain': {'product_id': [(1,'=',1)]}}



