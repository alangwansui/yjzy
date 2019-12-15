# -*- coding: utf-8 -*-
# Copyright 2017 Jarvis (www.odoomod.com)
# License LGPL-3.0 or later (http://www.gnu.org/licenses/lgpl.html).

import odoo.addons.decimal_precision as dp
from odoo import api, models, _, fields


class ProductProduct(models.Model):
    _inherit = "product.product"

    last_sale_price = fields.Float('最后销售价格', compute='_compute_last_sale_price', digits=dp.get_precision('Product Price'))

    @api.multi
    def get_last_sale_price(self, product_ids, partner_id=False):
        if partner_id:
            self.env.cr.execute('''
                select cond.product_id,l.price_unit 
                from (select o.partner_id,max(o.id) as id,l.product_id 
                    from sale_order o 
                    left join sale_order_line l on o.id = l.order_id 
                    where o.state in ('sale','done') and l.product_id in %(ids)s and o.partner_id = %(partner_id)s 
                    group by o.partner_id,l.product_id) cond 
                join sale_order_line l
                on cond.id = l.order_id and l.product_id=cond.product_id 
            ''', {'ids': tuple(product_ids),
                  'partner_id': partner_id})
            return {product_id: price_unit for product_id, price_unit in self.env.cr.fetchall()}
        else:
            self.env.cr.execute('''
                select cond.product_id,l.price_unit 
                from (select max(o.id) as id,l.product_id 
                    from sale_order o 
                    left join sale_order_line l on o.id = l.order_id 
                    where o.state in ('sale','done') and l.product_id in %(ids)s
                    group by l.product_id) cond 
                join sale_order_line l
                on cond.id = l.order_id and l.product_id=cond.product_id 
            ''', {'ids': tuple(product_ids),
                  'partner_id': partner_id})
            return {product_id: price_unit for product_id, price_unit in self.env.cr.fetchall()}

    @api.multi
    def _compute_last_sale_price(self):
        partner_id = self.env.context.get('partner_id')
        if len(self.ids) > 0:
            res = self.get_last_sale_price(self.ids, partner_id)
            for r in self:
                r.last_sale_price = res.get(r.id, False)

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        result = super(ProductProduct, self).name_search(name, args, operator, limit)
        context = self.env.context
        partner_id = context.get('partner_id')

        if ((partner_id and len(result) > 0) and ('pricelist' in context) and any(
                [arg[0] == 'sale_ok' for arg in args or []])) or (context.get('show_last_sale')):
            product_ids = [x[0] for x in result]

            if product_ids:
                res = self.get_last_sale_price(product_ids, partner_id)
                new_reslut = []
                for r in result:
                    price_unit = res.get(r[0])
                    if price_unit:
                        new_name = '%s %s :%s' % (r[1], _('LS'), price_unit)
                        new_reslut.append((r[0], new_name))
                    else:
                        new_reslut.append(r)
                result = new_reslut

        return result
