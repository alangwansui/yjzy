# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_multi_sale_line(models.TransientModel):
    _name = 'wizard.multi.sale.line'

    def compute_sale_order(self):
        return self.sol_ids.mapped('order_id')

    so_id = fields.Many2one('sale.order',u'销售合同')
    so_product_ids = fields.Many2many('product.product','ref_so_product_1', 'product_1_id', 'so_1_id', u'产品1')
    product_ids = fields.Many2many('product.product','ref_so_product', 'product_id', 'so_id', u'产品')
    sale_order_line_ids = fields.Many2many('sale.order.line','ref_so_soline', 'so_id', 'soline_id', u'原始订单')

    def apply(self):
        order_line_obj = self.env['sale.order.line']
        order_line_ids = order_line_obj.browse([]) #参考akiny |= 以及browse
        if self.product_ids:
            for one in self.product_ids:
                order_line = order_line_obj.create({
                    'product_id':one.id,
                    'order_id':self.so_id.id})
                order_line_ids |= order_line
            # for x in order_line_ids:
            #     x.product_id_change()







#####################################################################################################################
