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
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT


class SrMultiProductpurchase(models.TransientModel):
    _name = 'sr.multi.product.purchase'

    product_ids = fields.Many2many('product.product', string="Product")

    @api.multi
    def add_product(self):
        for line in self.product_ids:
            self.env['purchase.order.line'].create({
                'product_id': line.id,
                'name':line.name,
                'product_qty':1,
                'price_unit':line.standard_price,
                'order_id': self._context.get('active_id'),
                'date_planned':datetime.today().strftime(DEFAULT_SERVER_DATETIME_FORMAT),
                'product_uom' : line.uom_po_id.id or line.uom_id.id
            })
        return
