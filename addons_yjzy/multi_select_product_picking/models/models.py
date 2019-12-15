# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.exceptions import Warning

class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def open_multi_select_product(self):
        self.ensure_one()
        view = self.env.ref('multi_select_product_base.multi_select_product_tree')
        return {
            'name': _(u'添加产品明细'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            #'domain': domain,
        }

class product_product(models.Model):
    _inherit = 'product.product'

    @api.onchange('add_qty')
    def onchange_add_qty(self):
        res = super(product_product, self).onchange_add_qty()
        ctx = self.env.context
        add_qty = self.add_qty

        if ctx.get('active_model') == 'stock.picking' and add_qty:
            picking = self.env['sale.order'].browse(ctx.get('active_id'))
            self.onchange_add_qty4stock_move(picking, add_qty)
        return res

    def onchange_add_qty4stock_move(self, pick, add_qty):
        move_obj = self.env['stock.move']
        product = self._origin
        move = move_obj.create({
            'picking_id': pick.id,
            'name': product.name,
            'product_id': product.id,
            'product_uom_qty': add_qty,
            'product_uom': product.uom_id.id,
            'location_id': pick.location_id.id,
            'location_dest_id': pick.location_dest_id.id,
        })
        move.onchange_product_id()
        move.product_uom_qty = add_qty


    # def add_line_to_main_order(self):
    #     ctx = self.env.context
    #     if ctx.get('active_model') == 'stock.picking':
    #         pick = self.env['stock.picking'].browse(ctx.get('active_id'))
    #         self._add_line_to_picking(pick)
    #
    #     return super(product_product, self).add_line_to_main_order()
    #
    # def _add_line_to_picking(self, pick):
    #     move_obj = self.env['stock.move']
    #     product = self
    #     qty = product.add_qty or 1
    #     move = move_obj.create({
    #         'picking_id': pick.id,
    #         'name': product.name,
    #         'product_id': product.id,
    #         'product_uom_qty': qty,
    #         'product_uom': product.uom_id.id,
    #         'location_id': pick.location_id.id,
    #         'location_dest_id': pick.location_dest_id.id,
    #     })
    #     move.onchange_product_id()
    #     move.product_uom_qty = qty
