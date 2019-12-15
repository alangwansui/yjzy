# -*- coding: utf-8 -*-

from odoo import models, fields, api


class transport_lot_plan(models.Model):
    _name = 'transport.lot.plan'

    @api.depends('lot_id', 'qty')
    def compute_name(self):
        for one in self:
            one.name = '%s:%s' % (one.lot_id.name, one.qty)

    name = fields.Char('名称', compute=compute_name)
    tbline_id = fields.Many2one('transport.bill.line', u'发运明细', required=True, ondelete='cascade')
    lot_id = fields.Many2one('stock.production.lot', u'批次', required=True, ondelete='restrict')
    qty = fields.Float('数量')
    stage_1 = fields.Boolean('应用第1步')
    stage_2 = fields.Boolean('应用第2步')
    stage_3 = fields.Boolean('应用第3步')




