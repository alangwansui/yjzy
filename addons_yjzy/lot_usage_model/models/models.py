# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class stock_move(models.Model):
    _inherit = 'stock.move'

    def action_show_details(self):
        res = super(stock_move, self).action_show_details()
        if self.has_tracking != 'none':
            res['context'].update({
                'show_lots_m2o': self.picking_type_id.use_existing_lots or self.state == 'done' or self.origin_returned_move_id.id,
                'show_lots_text': self.picking_type_id.use_create_lots  and self.state != 'done' and not self.origin_returned_move_id.id,
            })
        return res

    def sale_check(self):
        for ml in self.move_line_ids:
            if ml.lot_name and ml.lot_id:
                raise Warning(u'不能同时使用新批次和旧批次')
        return True


class stock_move_line(models.Model):
    _inherit = 'stock.move.line'













