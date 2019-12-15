# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning


class wizard_bom_sale(models.TransientModel):
    _name = 'wizard.bom.sale'
    _description = '套件销售'

    bom_id = fields.Many2one('mrp.bom', u'BOM', required=True)
    product_id = fields.Many2one('product.product', u'产品', related='bom_id.product_id', readonly=True)
    qty = fields.Float('数量', default=1)

    def apply(self):
        so = self.env['sale.order'].browse(self.env.context.get('active_id'))
        sol_obj = self.env['sale.order.line']
        boms_done, lines_done = self.bom_id.explode(self.product_id, self.qty)

        for line in lines_done:
            product = line[0].product_id
            #print ('>>>>', product, line)
            sol = sol_obj.create({
                'name': product.name,
                'order_id': so.id,
                'product_id': product.id,
                'product_uom_qty': line[1]['qty'],
                'product_uom': product.uom_id.id,
                'price_unit': 1,
                'bom_id':  self.bom_id.id,
                'bom_qty': self.qty,
            })
            sol.product_id_change()

        return True







