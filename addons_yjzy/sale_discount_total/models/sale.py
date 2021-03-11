# -*- coding: utf-8 -*-
###################################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#    Copyright (C) 2017-TODAY Cybrosys Technologies(<https://www.cybrosys.com>).
#    Author: fasluca(<https://www.cybrosys.com>)
#
#    This program is free software: you can modify
#    it under the terms of the GNU Affero General Public License (AGPL) as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <https://www.gnu.org/licenses/>.
#
###################################################################################

from odoo import api, fields, models
import odoo.addons.decimal_precision as dp


class SaleOrder(models.Model):
    _inherit = "sale.order"



    @api.depends('order_line.price_total')
    def compute_amount_total_origin(self):
        for order in self:
            amount_untaxed_origin = amount_tax_origin = 0.0
            for line in order.order_line:
                amount_untaxed_origin += line.price_subtotal_origin
                amount_tax_origin += line.price_tax_origin
            order.update({
                'amount_untaxed_origin': order.pricelist_id.currency_id.round(amount_untaxed_origin),
                'amount_tax_origin': order.pricelist_id.currency_id.round(amount_tax_origin),
                'amount_total_origin': amount_untaxed_origin + amount_tax_origin,
            })

    @api.depends('order_line.price_total')
    def _amount_all(self):
        """
        Compute the total amounts of the SO.
        """
        for order in self:
            amount_untaxed = amount_tax = amount_discount = 0.0
            amount_total_origin = order.amount_total_origin
            for line in order.order_line:
                amount_untaxed += line.price_subtotal
                amount_tax += line.price_tax
                amount_discount = amount_total_origin -amount_untaxed + amount_tax
                order.update({
                    'amount_untaxed': order.pricelist_id.currency_id.round(amount_untaxed),
                    'amount_tax': order.pricelist_id.currency_id.round(amount_tax),
                    'amount_discount': order.pricelist_id.currency_id.round(amount_discount),
                    'amount_total': amount_untaxed + amount_tax,
                })




    amount_total_origin = fields.Monetary('原始金额', currency_field='currency_id', store=True, readonly=True,
                                          compute='compute_amount_total_origin', track_visibility='always')
    amount_untaxed_origin = fields.Monetary(string='原始未税金额', currency_field='currency_id', store=True, readonly=True,
                                            compute='compute_amount_total_origin',
                                            track_visibility='onchange')
    amount_tax_origin = fields.Monetary(string='原始税', store=True, readonly=True, compute='compute_amount_total_origin')

    discount_type = fields.Selection([('percent', '比例'), ('amount', '金额')], string='Discount type',
                                     readonly=True,states={'draft': [('readonly', False)], 'sent': [('readonly', False)]},
                                     default='percent')
    discount_rate = fields.Float('Discount Rate', digits=dp.get_precision('Account'),
                                 readonly=True, states={'draft': [('readonly', False)], 'sent': [('readonly', False)]})
    amount_untaxed = fields.Monetary(string='Untaxed Amount', store=True, readonly=True, compute='_amount_all',
                                     track_visibility='always')
    amount_tax = fields.Monetary(string='Taxes', store=True, readonly=True, compute='_amount_all',
                                 track_visibility='always')
    amount_total = fields.Monetary(string='Total', store=True, readonly=True, compute='_amount_all',
                                   track_visibility='always')
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_amount_all', currency_field='currency_id',
                                      track_visibility='always')

    @api.onchange('discount_type', 'discount_rate', 'order_line')
    def supply_rate(self):
        for order in self:
            if order.discount_type == 'percent':
                for line in order.order_line:
                    line.discount = order.discount_rate
            else:
                total = discount = 0.0
                for line in order.order_line:
                    total += round((line.product_uom_qty * line.price_unit))
                if order.discount_rate != 0:
                    discount = (order.discount_rate / total) * 100
                else:
                    discount = order.discount_rate
                for line in order.order_line:
                    line.discount = discount

    @api.multi
    def _prepare_invoice(self,):
        invoice_vals = super(SaleOrder, self)._prepare_invoice()
        invoice_vals.update({
            'discount_type': self.discount_type,
            'discount_rate': self.discount_rate
        })
        return invoice_vals

    @api.multi
    def button_dummy(self):
        self.supply_rate()
        return True


class AccountTax(models.Model):
    _inherit = 'account.tax'

    @api.multi
    def compute_all(self, price_unit, currency=None, quantity=1.0, product=None, partner=None):
        if len(self) == 0:
            company_id = self.env.user.company_id
        else:
            company_id = self[0].company_id
        if not currency:
            currency = company_id.currency_id
        taxes = []
        prec = currency.decimal_places
        round_tax = False if company_id.tax_calculation_rounding_method == 'round_globally' else True
        round_total = True
        if 'round' in self.env.context:
            round_tax = bool(self.env.context['round'])
            round_total = bool(self.env.context['round'])

        if not round_tax:
            prec += 5
        # total_excluded = total_included = base = round(price_unit * quantity, prec)
        total_excluded = total_included = base = (price_unit * quantity)

        for tax in self.sorted(key=lambda r: r.sequence):
            if tax.amount_type == 'group':
                ret = tax.children_tax_ids.compute_all(price_unit, currency, quantity, product, partner)
                total_excluded = ret['total_excluded']
                base = ret['base']
                total_included = ret['total_included']
                tax_amount = total_included - total_excluded
                taxes += ret['taxes']
                continue

            tax_amount = tax._compute_amount(base, price_unit, quantity, product, partner)
            if not round_tax:
                tax_amount = round(tax_amount, prec)
            else:
                tax_amount = currency.round(tax_amount)

            if tax.price_include:
                total_excluded -= tax_amount
                base -= tax_amount
            else:
                total_included += tax_amount
            
            tax_base = base
            
            if tax.include_base_amount:
                base += tax_amount

            taxes.append({
                'id': tax.id,
                'name': tax.with_context(**{'lang': partner.lang} if partner else {}).name,
                'amount': tax_amount,
                'sequence': tax.sequence,
                'account_id': tax.account_id.id,
                'refund_account_id': tax.refund_account_id.id,
                'analytic': tax.analytic,
                'base': tax_base,
            })
        return {
            'taxes': sorted(taxes, key=lambda k: k['sequence']),
            'total_excluded': total_excluded,
            'total_included': total_included,
            'base': base,
        }


class SaleOrderLine(models.Model):
    _inherit = "sale.order.line"

    @api.depends('product_uom_qty', 'discount', 'price_unit', 'tax_id')
    def _compute_amount_origin(self):
        """
        Compute the amounts of the SO line.
        """
        for line in self:
            discount = line.discount
            price_subtotal_origin = line.price_unit *  (1 - (0.0) / 100.0)
            amount_discount = line.price_unit * line.product_uom_qty * (discount / 100.0)
            taxes_origin = line.tax_id.compute_all(price_subtotal_origin,line.order_id.currency_id,
                                                   line.product_uom_qty,
                                                   product=line.product_id, partner=line.order_id.partner_shipping_id)

            line.update({
                'price_tax_origin': sum(t.get('amount', 0.0) for t in taxes_origin.get('taxes', [])),
                'price_total_origin': taxes_origin['total_included'],
                'price_subtotal_origin': taxes_origin['total_excluded'],
                'amount_discount':amount_discount
            })

    price_subtotal_origin = fields.Monetary(compute='_compute_amount_origin', string='原始未税金额', readonly=True,
                                            store=True)
    price_tax_origin = fields.Float(compute='_compute_amount_origin', string='税金', readonly=True, store=True)
    price_total_origin = fields.Monetary(compute='_compute_amount_origin', string='原价', readonly=True, store=True)
    amount_discount = fields.Monetary(string='Discount', store=True, readonly=True, compute='_compute_amount_origin',
                                      currency_field='currency_id',
                                      digits=dp.get_precision('Account'), track_visibility='always')



    discount = fields.Float(string='Discount (%)', digits=(16, 20), default=0.0)

