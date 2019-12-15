# -*- coding: utf-8 -*-

from odoo import models, fields, api


class wizard_manual_stock_reserve(models.TransientModel):
    _name = 'wizard.manual.stock.reserve'

    picking_id = fields.Many2one('stock.picking', u'调拨')
    line_ids = fields.One2many('wizard.manual.stock.reserve.line', 'wizard_id', u'明细')

    def apply(self):
        pick = self.picking_id
        ctx = self._context.copy()
        manual_reserve = {}
        for line in self.line_ids:
            manual_reserve[line.move_id] = {'lot': line.lot_id, 'qty': line.qty}
        ctx.update({'manual_reserve': manual_reserve})
        pick.with_context(ctx).action_assign()
        return True


class wizard_manual_stock_reserve_line(models.TransientModel):
    _name = 'wizard.manual.stock.reserve.line'

    wizard_id = fields.Many2one('wizard.manual.stock.reserve', 'wizard')
    move_id = fields.Many2one('stock.move', u'移动')
    product_id = fields.Many2one('product.product', u'产品', related='move_id.product_id')
    product_uom_qty = fields.Float(related='move_id.product_uom_qty', string=u'移库数量', readonly=True)
    reserved_availability = fields.Float(related='move_id.reserved_availability', string=u'已预留数量', readonly=True)
    lot_id = fields.Many2one('stock.production.lot', u'批次')
    qty = fields.Float(u'数量')
    item_ids = fields.One2many('wizard.manual.stock.reserve.item', 'line_id', u'Item')

    def apply(self):
        move = self.move_id
        move._do_unreserve()

        for i in self.item_ids:
            ctx = self.env.context.copy()
            manual_reserve = {
                'lot': i.new_lot_id,
                'qty': i.new_qty,
            }
            ctx.update({'manual_reserve': manual_reserve})
            move = self.move_id
            print('!!!', move, ctx)
            move.with_context(ctx)._action_assign()
        return True


class wizard_manual_stock_reserve_item(models.TransientModel):
    _name = 'wizard.manual.stock.reserve.item'

    line_id = fields.Many2one('wizard.manual.stock.reserve.line', u'Line')
    move_id = fields.Many2one('stock.move', related='line_id.move_id')
    product_id = fields.Many2one('product.product', u'产品', related='line_id.product_id')
    move_line_id = fields.Many2one('stock.move.line', u'Move Line', readonly=True)
    old_qty = fields.Float(related='move_line_id.product_uom_qty', string=u'已预留数量')
    new_lot_id = fields.Many2one('stock.production.lot', u'预留批次')
    new_qty = fields.Float(u'新预留数量')

    @api.onchange('move_line_id')
    def onchange_move_line(self):
        for one in self:
            one.new_lot_id = one.move_line_id.lot_id.id
