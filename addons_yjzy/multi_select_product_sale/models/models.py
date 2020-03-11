# -*- coding: utf-8 -*-
from datetime import datetime
from odoo import models, fields, api, _
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DTF
from odoo.exceptions import Warning


class sale_order(models.Model):
    _inherit = 'sale.order'

    def open_multi_select_product(self):
        view = self.env.ref('multi_select_product_base.multi_select_product_tree')
        return {
            'name': _(u'添加产品明细'),
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'product.product',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'domain': [('sale_ok', '=', True)],
        }


class product_product(models.Model):
    _inherit = 'product.product'

    @api.onchange('add_qty')
    def onchange_add_qty(self):
        res = super(product_product, self).onchange_add_qty()
        ctx = self.env.context
        add_qty = self.add_qty
        add_price = self.add_price

        if ctx.get('active_model') == 'sale.order' and add_qty:
            so = self.env['sale.order'].browse(ctx.get('active_id'))
            self.onchange_add_qty4sol(so, add_qty, add_price)
        return res

    def onchange_add_qty4sol(self, so, add_qty, add_price):
        sol_obj = self.env['sale.order.line']
        product = self._origin
        print ('=========', product, product.add_qty, product.name)
        sol = sol_obj.create({
            'order_id': so.id,
            'name': product.name,
            'product_id': product.id,
            'product_uom': product.uom_id.id,
            'price_unit': add_price,
            'product_uom_qty': add_qty,
            'date_planned': datetime.today().strftime(DTF),
            'back_tax': product.back_tax,
        })
        sol.product_id_change()
        sol.product_uom_qty = add_qty


    # def add_line_to_main_order(self):
    #     ctx = self.env.context
    #     if ctx.get('active_model') == 'sale.order':
    #         so = self.env['sale.order'].browse(ctx.get('active_id'))
    #         self._add_line_to_so(so)
    #
    #     return super(product_product, self).add_line_to_main_order()
    #
    # def _add_line_to_so(self, so):
    #     sol_obj = self.env['sale.order.line']
    #     product = self
    #     qty = product.add_qty or 1
    #     print ('=========', product, product.name)
    #     sol = sol_obj.create({
    #         'order_id': so.id,
    #         'name': product.name,
    #         'product_id': product.id,
    #         'product_uom': product.uom_id.id,
    #         'price_unit': 1,
    #         'product_uom_qty': qty,
    #         'date_planned': datetime.today().strftime(DTF)
    #     })
    #     sol.product_id_change()
    #     sol.product_uom_qty = qty
