# -*- coding: utf-8 -*-

from odoo import models, fields, api


class Stock_Move_Line(models.Model):
    _inherit = "stock.move.line"

    @api.multi
    def total_reserved_qty(self):
        qty = 0.0
        for i in self:
            qty += i.state == 'done' and not i.move_id.picking_id.is_return and i.move_id.picking_id.pick_type != 'return' and i.qty_done or i.product_uom_qty
        return qty

    def _action_done(self):
        '''采购入库后，自动锁定采购预留的相关销售出库'''
        res = super(Stock_Move_Line, self)._action_done()
        print('====Stock_Move_Line _action_done=', self, self.env.context)

        in_pick_type = self.env.ref('stock.picking_type_in')
        out_pick_type = self.env.ref('stock.picking_type_out')

        wizard_obj = self.env['wizard.manual.stock.reserve.line']
        item_obj = self.env['wizard.manual.stock.reserve.item']

        for ml in self:
            lot = ml.lot_id
            if not lot or ml.picking_id.picking_type_id != in_pick_type:
                continue

            move = ml.move_id
            pol = move.purchase_line_id
            print('====po', pol.order_id.name)
            dlr_records = self.env['dummy.lot.reserve'].search([('lot_id', '=', lot.id), ('pol_id', '=', pol.id)])
            print('====dlrs', dlr_records)
            for dlr in dlr_records:
                out_move = dlr.sol_id.move_ids.filtered(lambda m: m.picking_type_id == out_pick_type
                                                                  and m.state not in ['cancel', 'done', 'draft'])
                wizard = wizard_obj.create({'move_id': out_move.id})
                have_ml = out_move.move_line_ids.filtered(lambda m: m.lot_id == lot)
                item_obj.create({
                    'line_id': wizard.id,
                    'move_line_id': have_ml and have_ml[0].id,
                    'new_lot_id': not have_ml and lot.id,
                    'new_qty': dlr.qty,
                })
                wizard.apply()
        return res


class stock_move(models.Model):
    _inherit = 'stock.move'

    def _prepare_move_line_vals(self, quantity=None, reserved_quant=None):
        '''采购订单，自动使用采购批次号'''

        res = super(stock_move, self)._prepare_move_line_vals(quantity=quantity, reserved_quant=reserved_quant)
        if self.purchase_line_id and self.product_id.tracking == 'lot':
            lot = self.env['stock.production.lot'].search([
                ('product_id', '=', self.product_id.id),
                ('po_id', '=', self.purchase_line_id.order_id.id)], limit=1)
            if lot:
                res['lot_id'] = lot.id

        return res

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    # @api.multi
    # def action_done(self):
    #     res = super(stock_picking,self).action_done()
    #     pick_type = self.env.ref('stock.picking_type_in')
    #     pickings = self.filtered(lambda x: x.picking_type == pick_type)
    #     if pickings:
    #         for p in pickings:
    #             p.acton_lot_sale_reserve()
    #     return res
    #
    # def acton_lot_sale_reserve(self):
    #     self.ensure_one()

    is_return = fields.Boolean('是否被退货')
    pick_type = fields.Selection([('normal','正常'),('return','退货'),('scrap','报废')],'调拨类型')


class stock_quant(models.Model):
    _inherit = 'stock.quant'
    _rec_name = 'name'


    def compute_name(self):
        for one in self:
            one.name = '%s %s %s 可用%s' % (one.product_id.name, one.location_id.name, one.lot_id.name,  one.available_quantity)

    def compute_available_quantity(self):
        for one in self:
            one.available_quantity = one.quantity - one.reserved_quantity


    name = fields.Char('name', compute='compute_name')
    available_quantity = fields.Float('可用数量', compute='compute_available_quantity')

    def _gather(self, product_id, location_id, lot_id=None, package_id=None, owner_id=None, strict=False):
        quants = super(stock_quant, self)._gather(product_id, location_id, lot_id=lot_id, package_id=package_id, owner_id=owner_id,
                                                  strict=strict)
        print('_gather berore___', quants)
        if 'limit_lot_ids' in self._context:
            limit_lot_ids = self._context.get('limit_lot_ids', False)
            quants = quants.filtered(lambda p: p.lot_id.id in limit_lot_ids)
        print('_gather after___', quants)
        return quants
