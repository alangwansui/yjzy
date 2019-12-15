# -*- coding: utf-8 -*-

from odoo import models, fields, api


class dummy_lot_reserve(models.Model):
    _name = 'dummy.lot.reserve'
    _description = u'虚拟预留'

    def compute_info(self):
        for o in self:
            smlines = o.sol_id.smline_ids.filtered(lambda x: x.lot_id == o.lot_id)
            done_qty = smlines.total_reserved_qty()
            todo_qty = o.qty - done_qty

            o.done_qty = done_qty
            o.todo_qty = todo_qty
            o.name = '%s:%s' % (o.lot_id.name, todo_qty)
            o.purchase_amount = o.pol_id.price_unit * o.qty

    name = fields.Char(u'预留', compute=compute_info)
    sol_id = fields.Many2one('sale.order.line', u'销售明细', required=True, ondelete='cascade')
    lot_id = fields.Many2one('stock.production.lot', u'批次', required=True, ondelete='cascade')
    qty = fields.Float(u'计划预留数')

    product_id = fields.Many2one('product.product', related='sol_id.product_id', string=u'产品', readonly=True)
    pol_id = fields.Many2one('purchase.order.line', related='lot_id.pol_id', string=u'采购明细', readonly=True)
    so_id = fields.Many2one('sale.order', related='sol_id.order_id', string=u'销售订单', readonly=True)
    po_id = fields.Many2one('purchase.order', related='pol_id.order_id', string=u'采购订单', readonly=True)
    done_qty = fields.Float(u'预留完成数', compute=compute_info)
    todo_qty = fields.Float(u'待预留数', compute=compute_info)
    state = fields.Selection([('draft', u'草稿'), ('done', u'完成')], '状态', default='draft')

    purchase_currency_id = fields.Many2one('res.currency', u'采购货币', related='po_id.currency_id', readonly=True)
    purchase_amount = fields.Monetary(u'采购金额', compute=compute_info, currency_field='purchase_currency_id')


    @api.constrains('pol_id', 'qty')
    def check_po_qty(self):
        for one in self:
            one.pol_id.compute_dlr()


