# -*- coding: utf-8 -*-

from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.exceptions import Warning

class purchase_order(models.Model):
    _inherit = 'purchase.order'

    def open_multi_select_product(self):
        self.ensure_one()
        view = self.env.ref('multi_select_product_base.multi_select_product_tree')
        domain = [('purchase_ok','=',True)]
        return {
            'name': _(u'添加产品明细'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'domain': domain,
        }

class product_product(models.Model):
    _inherit = 'product.product'

    @api.onchange('add_qty')
    def onchange_add_qty(self):
        res = super(product_product, self).onchange_add_qty()
        ctx = self.env.context
        add_qty = self.add_qty

        if ctx.get('active_model') == 'purchase.order' and add_qty:
            po = self.env['sale.order'].browse(ctx.get('active_id'))
            self.onchange_add_qty4pol(po, add_qty)
        return res

    def onchange_add_qty4pol(self, po, add_qty):
        pol_obj = self.env['purchase.order.line']
        product = self._origin
        pol = pol_obj.create({
            'order_id': po.id,
            'name': product.name,
            'product_id': product.id,
            'product_uom':  product.uom_id.id,
            'price_unit': 1,
            'product_qty': add_qty,
            'date_planned': datetime.today().strftime(DTF)
        })
        pol.onchange_product_id()
        pol.product_qty = add_qty


    # def add_line_to_main_order(self):
    #     ctx = self.env.context
    #     if ctx.get('active_model') == 'purchase.order':
    #         po = self.env['purchase.order'].browse(ctx.get('active_id'))
    #         self._add_line_to_po(po)
    #
    #     return super(product_product, self).add_line_to_main_order()
    #
    # def _add_line_to_po(self, po):
    #     pol_obj = self.env['purchase.order.line']
    #     product = self
    #     qty = product.add_qty or 1
    #     pol = pol_obj.create({
    #         'order_id': po.id,
    #         'name': product.name,
    #         'product_id': product.id,
    #         'product_uom':  product.uom_id.id,
    #         'price_unit': 1,
    #         'product_qty': qty,
    #         'date_planned': datetime.today().strftime(DTF)
    #     })
    #     pol.onchange_product_id()
    #     pol.product_qty = qty