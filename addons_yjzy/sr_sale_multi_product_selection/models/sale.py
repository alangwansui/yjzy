# -*- coding: utf-8 -*-
##############################################################################
#
#    This module uses OpenERP, Open Source Management Solution Framework.
#    Copyright (C) 2017-Today Sitaram
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU General Public License as published by
#    the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU General Public License for more details.
#
#    You should have received a copy of the GNU General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>
#
##############################################################################

from odoo import api, fields, models


class SrMultiProduct(models.TransientModel):
    _name = 'sr.multi.product'

    product_ids = fields.Many2many('product.product', string="Product")
    partner_id = fields.Many2one('res.partner', '客户')

    @api.multi
    def add_product(self):
        for line in self.product_ids:
            print('==', line.variant_seller_ids and line.variant_seller_ids[0].name)
            self.env['sale.order.line'].create({
                'product_id': line.id,
                'order_id': self._context.get('active_id'),
                'supplier_id': line.variant_seller_ids and line.variant_seller_ids[0].name.id or None,
                'purchase_price': line.variant_seller_ids and line.variant_seller_ids[0].price or 0,
                's_uom_id': line.s_uom_id.id,
                'p_uom_id': line.p_uom_id.id,
                'need_split_bom':line.need_split_bom,
                'need_print':line.need_print,
                'back_tax':line.back_tax,
            })
        return

class sale_order(models.Model):
    _inherit = 'sale.order'

    def open_elect_multi_product_wizard(self):
        return {
            'name': u'产品多选',
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'target': 'new',
            'res_model': 'sr.multi.product',
            'context': {'default_partner_id': self.partner_id.id}
        }



