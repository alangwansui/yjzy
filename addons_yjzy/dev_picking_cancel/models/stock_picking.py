# -*- coding: utf-8 -*-
##############################################################################
#
#    OpenERP, Open Source Management Solution
#    Copyright (C) 2015 DevIntelle Consulting Service Pvt.Ltd (<http://www.devintellecs.com>).
#
#    For Module Support : devintelle@gmail.com  or Skype : devintelle 
#
##############################################################################
from odoo import api,  models, _
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT
from odoo.tools.float_utils import float_round, float_is_zero

class stock_picking(models.Model):
    _inherit = 'stock.picking'
    
    
    @api.multi
    def action_cancel(self):
        res = super(stock_picking,self).action_cancel()
        if self.picking_type_id.code == 'incoming':
            account_pool=self.env['account.move']
            move_ids = account_pool.search([('ref','=',self.name),('state','=','posted')])
            move_ids.sudo().button_cancel()
            move_ids.sudo().unlink()


    @api.multi
    def action_set_draft(self):
        move_obj = self.env['stock.move']
        for pick in self:
            ids2 = [move.id for move in pick.move_lines]
            moves = move_obj.browse(ids2)
            moves.sudo().action_draft()
        return True


class stock_move(models.Model):
    _inherit = 'stock.move'
    
    @api.multi
    def action_draft(self):
        res = self.write({'state': 'draft'})
        return res
    
    def _do_unreserve(self):
        for stok_move in self:
            stok_move.move_line_ids.unlink()
            if stok_move.procure_method == 'make_to_order' and not stok_move.move_orig_ids:
                stok_move.state = 'waiting'
            elif stok_move.move_orig_ids and not all(orig.state in ('done', 'cancel') for orig in stok_move.move_orig_ids):
                stok_move.state = 'waiting'
            else:
                stok_move.state = 'confirmed'
        return True


    @api.multi
    def set_quantity(self,move_qty, product,location,sign):
        out_qaunt = self.env['stock.quant'].sudo().search([('product_id','=',product.id),('location_id','=',location.id)])
        if out_qaunt:
            quantity = out_qaunt[0].quantity
            if sign == 'sub':
                out_qaunt[0].quantity = quantity - move_qty
            else:
                out_qaunt[0].quantity = quantity + move_qty


    @api.multi
    def set_quant_quantity(self,stock_move,pack_operation_ids):
        for pack_operation_id in pack_operation_ids:
            if stock_move.picking_id.picking_type_id.code in ['outgoing','internal']:
                if stock_move.picking_id.sale_id.warehouse_id.delivery_steps == 'pick_ship':
                    if pack_operation_id.location_dest_id.usage == 'customer':
                        self.set_quantity(stock_move.product_uom_qty,stock_move.product_id,pack_operation_id.location_dest_id,'sub')
                    else:
                        self.set_quantity(stock_move.product_uom_qty,stock_move.product_id,pack_operation_id.location_id,'add')
                else:
                    self.set_quantity(stock_move.product_uom_qty,stock_move.product_id,pack_operation_id.location_id,'add')

            if stock_move.picking_id.picking_type_id.code == 'incoming':
                self.set_quantity(stock_move.product_uom_qty,stock_move.product_id,pack_operation_id.location_dest_id,'sub')
        return True

    @api.multi    
    def _action_cancel(self):
        for move in self:
            move._do_unreserve()
            siblings_states = (move.move_dest_ids.mapped('move_orig_ids') - move).mapped('state')
            if move.propagate:
                if all(state == 'cancel' for state in siblings_states):
                    move.move_dest_ids._action_cancel()
            else:
                if all(state in ('done', 'cancel') for state in siblings_states):
                    move.move_dest_ids.write({'procure_method': 'make_to_stock'})
                    move.move_dest_ids.write({'move_orig_ids': [(3, move.id, 0)]})
        
            if move.picking_id.state == 'done' or 'confirmed':
                pack_op = self.env['stock.move'].sudo().search([('picking_id','=',move.picking_id.id),('product_id','=',move.product_id.id)])
                self.set_quant_quantity(move,pack_op) 
                    
            self.write({'state': 'cancel', 'move_orig_ids': [(5, 0, 0)]})
        return True

class stock_move_line(models.Model):
    _inherit = "stock.move.line"
    
    def unlink(self):
        uom_precision = self.env['decimal.precision'].precision_get('Product Unit of Measure')
        for move_line in self:
            if move_line.product_id.type == 'product' and not move_line.location_id.should_bypass_reservation() and not float_is_zero(move_line.product_qty, precision_digits=uom_precision):
                self.env['stock.quant']._update_reserved_quantity(move_line.product_id, move_line.location_id, -move_line.product_qty, lot_id=move_line.lot_id,package_id=move_line.package_id, owner_id=move_line.owner_id, strict=True)
        return 

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:            
