# -*- coding: utf-8 -*-

from odoo import models, fields, api


class stock_picking(models.Model):
    _inherit = 'stock.picking'

    def open_wizard_manual_stock_reserve(self):
        self.ensure_one()
        wl_obj = self.env['wizard.manual.stock.reserve.line']
        wizard = self.env['wizard.manual.stock.reserve'].create({'picking_id': self.id})
        for move in self.move_lines:
            wl_obj.create({'wizard_id': wizard.id, 'move_id': move.id, })

        return {
            'name': u'手动预留',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.manual.stock.reserve',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }


class stock_move(models.Model):
    _inherit = 'stock.move'

    def _update_reserved_quantity(self, need, available_quantity, location_id, lot_id=None, package_id=None,
                                  owner_id=None, strict=True):
        # 替换需要手动指定的批次，和需要的数量
        manual_reserve = self._context.get('manual_reserve')
        if manual_reserve:
            print('===', manual_reserve)
            manual_need = manual_reserve.get('qty')
            lot_id = manual_reserve.get('lot')
            need = min(manual_need, need)
        return super(stock_move, self)._update_reserved_quantity(need, available_quantity, location_id, lot_id=lot_id,
                                                                 package_id=package_id,
                                                                 owner_id=owner_id, strict=strict)

    def open_manual_reserve(self):
        self.ensure_one()
        item_obj = self.env['wizard.manual.stock.reserve.item']
        wizard = self.env['wizard.manual.stock.reserve.line'].create({'move_id': self.id})
        for ml in self.move_line_ids:
            item_obj.create({
                'line_id': wizard.id,
                'move_line_id': ml.id,
                'new_lot_id': ml.lot_id.id,
                'new_qty': ml.product_uom_qty,
            })

        return {
            'name': u'手动预留',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.manual.stock.reserve.line',
            'res_id': wizard.id,
            'type': 'ir.actions.act_window',
            'target': 'new',
        }
