# -*- coding: utf-8 -*-

from odoo import  fields, models, api, _
from odoo.exceptions import Warning

class wizard_sol_reserver(models.TransientModel):
    _name = 'wizard.sol.reserver'

    sol_id = fields.Many2one('sale.order.line', u'销售明细')
    product_id = fields.Many2one('product.product', related='sol_id.product_id')
    line_ids = fields.One2many('wizard.sol.reserver.item', 'wizard_id', u'明细')

    def apply(self):
        self.ensure_one()
        dlr_obj = self.env['dummy.lot.reserve']
        for line in self.line_ids:
            data = {'lot_id': line.lot_id.id, 'qty': line.qty}
            dlr = line.dlr_id
            if dlr:
                dlr.write(data)
            else:
                data.update({'sol_id': self.sol_id.id})
                dlr = dlr_obj.create(data)

class wizard_sol_reserver_item(models.TransientModel):
    _name = 'wizard.sol.reserver.item'

    wizard_id = fields.Many2one('wizard.sol.reserver', 'wizard')
    dlr_id = fields.Many2one('dummy.lot.reserve', u'预留')
    lot_id = fields.Many2one('stock.production.lot', u'批次')
    qty = fields.Float(u'计划预留数')

    @api.onchange('dlr_id')
    def onchange_dlr(self):
        dlr = self.dlr_id
        if dlr:
            self.lot_id = dlr.lot_id
            self.qty = dlr.qty

    def unlink_dlr(self):
        self.ensure_one()
        if self.dlr_id:
            self.dlr_id.unlink()
        self.unlink()
