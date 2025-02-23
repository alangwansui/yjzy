# -*- coding: utf-8 -*-
# Copyright 2015 Oihane Crucelaegui - AvanzOSC
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2016 ACSONE SA/NV
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3

from odoo import api, fields, models
from odoo.addons import decimal_precision as dp


class ProductConfiguratorAttribute(models.Model):
    _name = 'product.configurator.attribute'
    _order = 'attribute_id'

    owner_id = fields.Integer(
        string="Owner",
        required=True,
        # ondelete is required since the owner_id is declared as inverse
        # of the field product_attribute_ids of the abstract model
        # product.configurator
        ondelete='cascade')
    owner_model = fields.Char(required=True)
    product_tmpl_id = fields.Many2one(
        comodel_name='product.template', string='Product Template',
        required=True)
    attribute_id = fields.Many2one(comodel_name='product.attribute', string='Attribute', readonly=True, index=True)
    value_id = fields.Many2one(
        comodel_name='product.attribute.value',
        domain="[('attribute_id', '=', attribute_id), ('id', 'in', possible_value_ids)]",
        string='Value')
    possible_value_ids = fields.Many2many(
        comodel_name='product.attribute.value',
        compute='_compute_possible_value_ids',
        readonly=True)

    price_extra = fields.Float(
        compute='_compute_price_extra',
        digits=dp.get_precision('Product Price'),
        help="Price Extra: Extra price for the variant with this attribute "
             "value on sale price. eg. 200 price extra, 1000 + 200 = 1200.")

    @api.depends('attribute_id')
    def _compute_possible_value_ids(self):
        for record in self:
            # This should be unique due to the new constraint added
            line = record.product_tmpl_id.attribute_line_ids.filtered(lambda x: x.attribute_id == record.attribute_id)
            possible_value = line.value_ids
            if not possible_value:
                possible_value = self.env['product.attribute.value'].search([('attribute_id','=', record.attribute_id.id)])
            record.possible_value_ids = possible_value.sorted()

    @api.depends('value_id')
    def _compute_price_extra(self):
        for record in self:
            record.price_extra = sum(
                record.value_id.price_ids.filtered(
                    lambda x: (
                        x.product_tmpl_id == record.product_tmpl_id)
                ).mapped('price_extra'))
