# -*- coding: utf-8 -*-
##############################################
#
# Difusión Visual
# Copyright (C) Difusión Visual
# all rights reserved
# http://difusionvisual.com
# contacto@difusionvisual.com
#
# WARNING: This program as such is intended to be used by professional
# programmers who take the whole responsability of assessing all potential
# consequences resulting from its eventual inadequacies and bugs.
# End users who are looking for a ready-to-use solution with commercial
# garantees and support are strongly adviced to contract a Free Software
# Service Company.
#
# This program is Free Software; you can redistribute it and/or
# modify it under the terms of the GNU Affero General Public License
# as published by the Free Software Foundation; either version 3
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program; if not, see <http://www.gnu.org/licenses/> or
# write to the Free Software Foundation, Inc.,
# 59 Temple Place - Suite 330, Boston, MA  02111-1307, USA.
#
###############################################

from odoo import api, fields, models, _

from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError, ValidationError
from odoo.tools.float_utils import float_round, float_compare
from odoo.exceptions import Warning

class StockMove(models.Model):
    _inherit = 'stock.move'

    @api.model
    def _prepare_procurement_from_move(self, move):
        vals = super(StockMove, self)._prepare_procurement_from_move(move)
        vals['lot_id'] = move.restrict_lot_id.id
        vals['qty'] = move.order_qty
        return vals


class procurement_order(models.Model):
    _inherit = 'procurement.order'

    lot_id = fields.Many2one('stock.production.lot', 'Lot')
    order_qty = fields.Float(string="Qty",  required=False, )

    @api.model
    def _get_stock_move_values(self):
        res = super(
            procurement_order, self)._get_stock_move_values()
        res['restrict_lot_id'] = self.lot_id.id
        res['qty_done'] = self.order_qty
        return res


class StockPickingLot(models.Model):
    _inherit = 'stock.picking'

    @api.one
    def set_pack_operation_lot_assign(self):
        self.ensure_one()
        for order in self:
            for pack_operation in order.pack_operation_product_ids:

                qty_done = pack_operation.product_qty
                pack_operation.write({'qty_done': qty_done})
                for lots in pack_operation.pack_lot_ids:
                    qty_todo = lots.qty_todo
                    lots.write({'qty': qty_todo})


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    lot_id = fields.Many2one(
        'stock.production.lot', 'Lot', copy=False)

    @api.onchange('product_id')
    def _onchange_product_id_set_lot_domain(self):
        available_lot_ids = []
        if self.order_id.warehouse_id and self.product_id:
            location = self.order_id.warehouse_id.lot_stock_id
            quants = self.env['stock.quant'].read_group([
                ('product_id', '=', self.product_id.id),
                ('location_id', 'child_of', location.id),
                ('qty', '>', 0),
                ('lot_id', '!=', False),
            ], ['lot_id'], 'lot_id')
            available_lot_ids = [quant['lot_id'][0] for quant in quants]
        self.lot_id = False
        return {
            'domain': {'lot_id': [('id', 'in', available_lot_ids)]}
        }

    @api.multi
    def _prepare_order_line_procurement(self, group_id=False):
        res = super(
            SaleOrderLine, self)._prepare_order_line_procurement(
            group_id=group_id)
        res['lot_id'] = self.lot_id.id
        res['order_qty'] = self.product_uom_qty
        return res


class SaleOrder(models.Model):
    _inherit = "sale.order"

    @api.model
    def get_move_from_line(self, line):
        move = self.env['stock.move']
        # i create this counter to check lot's univocity on move line
        lot_count = 0
        for p in line.order_id.picking_ids:
            for m in p.move_lines:
                if line.lot_id == m.restrict_lot_id:
                    move = m
                    lot_count += 1
                    # if counter is 0 or > 1 means that something goes wrong
                    if lot_count != 1:
                        raise Warning(_('Can\'t retrieve lot on stock'))
        return move

    @api.model
    def _check_move_state(self, line):
        if line.lot_id:
            move = self.get_move_from_line(line)
            if move.state == 'confirmed':
                move.action_assign()
                move.refresh()
            if move.state != 'assigned':
                raise Warning(_('Can\'t reserve products for lot %s') %
                              line.lot_id.name)
        return True

    @api.multi
    def action_confirm(self):
        res = super(SaleOrder, self).action_confirm()
        for line in self.order_line:
            self._check_move_state(line)
        return res