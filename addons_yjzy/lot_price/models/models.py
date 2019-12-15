# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.addons import decimal_precision as dp


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'

    #purchase_price = fields.Float(u'采购价格', digits=dp.get_precision('Product Price'))
    #pol_id = fields.Many2one('purchase.order.line', u'采购明细')
    #po_id = fields.Many2one('purchase.order', related='pol_id.order_id', string=u'采购单号', readonly=True)
    #supplier_id = fields.Many2one('res.partner',  related='po_id.partner_id', stirng=u'供应商', readonly=True)
    #dummy_qty = fields.Float(u'u采购数量')


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    # def button_confirm(self):
    #     self.ensure_one()
    #     lot_obj = self.env['stock.production.lot']
    #     for line in self.order_line:
    #         lot_obj.create({
    #             'name': self.name,
    #             'product_id': line.product_id.id,
    #             'pol_id': line.id,
    #             'purchase_price': line.price_unit,
    #             'dummy_qty': line.product_qty,
    #         })
    #
    #     res = super(purchase_order, self).button_confirm()
    #     return res


class stock_move(models.Model):
    _inherit = 'stock.move'

    # def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
    #     '''采购订单，自动使用采购批次号'''
    #
    #     res = super(stock_move, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
    #     if self.purchase_line_id and self.product_id.tracking == 'lot':
    #         lot = self.env['stock.production.lot'].search([
    #             ('product_id', '=', self.product_id.id),
    #             ('po_id', '=', self.purchase_line_id.order_id.id)], limit=1)
    #         if lot:
    #             res['lot_id'] = lot.id
    #
    #     return res
