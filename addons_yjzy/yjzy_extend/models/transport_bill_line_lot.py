# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class bill_line_lot(models.Model):
    _name = 'bill.line.lot'
    _description = u'发货单明细批次'

    tb_line_id = fields.Many2one('transport.bill.line', u'发运明细')
    product_id = fields.Many2one('product.product', related='tb_line_id.product_id', string=u'产品')
    tbv_id = fields.Many2one('transport.bill.vendor', u'供应商发运单')

    tb_id = fields.Many2one('transport.bill', u'发运单')
    lot_id = fields.Many2one('stock.production.lot', u'批次号')
    qty = fields.Float('数量')
    po_id = fields.Many2one(related='lot_id.po_id')
    so_id = fields.Many2one(related='tb_line_id.so_id')

    qty_package = fields.Float(u'包装数量')
    package_qty = fields.Float(u'每包数量')


