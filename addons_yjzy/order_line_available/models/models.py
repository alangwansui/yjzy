# -*- coding: utf-8 -*-

from odoo import models, fields, api


class sale_order_line(models.Model):
    _inherit = 'sale.order.line'

    qty_available = fields.Float('在手数', related='product_id.qty_available')
    virtual_available = fields.Float('预测数', related='product_id.virtual_available')


class purchase_order_line(models.Model):
    _inherit = 'purchase.order.line'

    qty_available = fields.Float('在手数', related='product_id.qty_available')
    virtual_available = fields.Float('预测数', related='product_id.virtual_available')


class stock_move(models.Model):
    _inherit = 'stock.move'

    qty_available = fields.Float('在手数', related='product_id.qty_available')
    virtual_available = fields.Float('预测数', related='product_id.virtual_available')
