# -*- coding: utf-8 -*-

from odoo import models, fields, api



class product_pricelist(models.Model):
    _inherit = "product.pricelist"

    type = fields.Selection([('public', u'共用'), ('special', u'专用')], u'类型', default='public')


class sale_order(models.Model):
    _inherit = "sale.order"

    @api.multi
    def action_confirm(self):
        res = super(sale_order, self).action_confirm()
        for order in self:
            if order.pricelist_id.type == 'special':
                order.update_pricelist()

        return res

    @api.multi
    def update_pricelist(self):
        self.ensure_one()
        item_obj = self.env['product.pricelist.item']

        pricelist = self.pricelist_id
        dic = dict([(x.product_id.id, x) for x in pricelist.item_ids])
        for line in self.order_line:
            if line.product_id.id in dic:
                item = dic[line.product_id.id]
                if item.compute_price == 'fixed':
                    item.fixed_price = line.price_unit
            else:
                item_obj.create({
                    'applied_on': '0_product_variant',
                    'product_id': line.product_id.id,
                    'pricelist_id': pricelist.id,
                    'compute_price': 'fixed',
                    'fixed_price': line.price_unit,
                })

        return True


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super(purchase_order, self).button_confirm()
        for one in self:
            one.update_supplier_price()
        return res

    def button_approve(self):
        res = super(purchase_order, self).button_approve()
        for one in self:
            one.update_supplier_price()
        return res

    def update_supplier_price(self):
        self.ensure_one()
        seller_obj = self.env['product.supplierinfo']
        for line in self.order_line:
            # seller = self.product_id._select_seller(
            #     partner_id=line.partner_id,
            #     quantity=line.product_qty,
            #     date=line.order_id.date_order and line.order_id.date_order[:10],
            #     uom_id=line.product_uom)

            seller = line.product_id.seller_ids.filtered(lambda x: x.name == self.partner_id)



            #print('====', line.product_id,  line.product_id.seller_ids,  seller, seller.product_id)

            if not seller:
                seller = seller_obj.create({
                    'name': self.partner_id.id,
                    'product_name': line.product_id.name,
                    'product_uom': line.product_uom.id,
                    'price': line.price_unit,
                    'product_id': line.product_id.id,
                })
            else:
                if seller[0].price != line.price_unit:
                    seller[0].price = line.price_unit
        #raise Warning('==')
