# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp


class stock_production_lot(models.Model):
    _inherit = 'stock.production.lot'


    pol_id = fields.Many2one('purchase.order.line', u'采购明细', ondelete='cascade')
    purchase_price = fields.Float(u'采购价格', related='pol_id.price_unit')
    po_id = fields.Many2one('purchase.order', related='pol_id.order_id', string=u'采购单号', readonly=True)
    supplier_id = fields.Many2one('res.partner',  related='po_id.partner_id', stirng=u'供应商', readonly=True)
    dummy_qty = fields.Float(u'u采购数量')

    @api.multi
    def name_get(self):
        ctx = self.env.context
        res = []
        for one in self:

            name = one.name
            if ctx.get('show_po_code'):
                name = '%s' % one.po_id.contract_code
            res.append((one.id, name))
        return res