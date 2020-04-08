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

from odoo import fields, models, api
from datetime import datetime
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT

class SrCreateRequestForQuotation(models.TransientModel):
    _name = "sr.create.request.for.quotation"

    partner_id = fields.Many2one('res.partner', string="Partner", domain=[('supplier','=',True)])

    @api.multi
    def create_request_for_quotation(self):
        pur_id = self.env['purchase.order'].create({'partner_id': self.partner_id.id})
        for product in self._context.get('active_ids'):
            line = self.env['product.product'].browse(product)
            self.env['purchase.order.line'].create({'product_id': product,
                                                'order_id': pur_id.id,
                                                    'name': line.name,
                                                    'product_qty': 1,
                                                    'price_unit': line.standard_price,
                                                    'date_planned': datetime.today().strftime(
                                                        DEFAULT_SERVER_DATETIME_FORMAT),
                                                    'product_uom': line.uom_po_id.id or line.uom_id.id
            })

        action = self.env.ref('purchase.purchase_rfq').read()[0]
        action['views'] = [(self.env.ref('purchase.purchase_order_form').id, 'form')]
        action['res_id'] = pur_id.ids[0]
        return action
