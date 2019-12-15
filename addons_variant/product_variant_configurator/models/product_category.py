# -*- coding: utf-8 -*-
# Copyright 2015 Oihane Crucelaegui - AvanzOSC
# Copyright 2016 Pedro M. Baeza <pedro.baeza@tecnativa.com>
# Copyright 2016 ACSONE SA/NV
# License AGPL-3 - See http://www.gnu.org/licenses/agpl-3

from odoo import _, api, fields, models


class CategoryAttributeLine(models.Model):
    _name = 'category.attribute.line'

    categ_id = fields.Many2one('product.category', u'产品分类', ondelete='cascade', required=True)
    attribute_id = fields.Many2one('product.attribute', u'属性', ondelete='restrict', required=True)
    value_ids = fields.Many2many('product.attribute.value', string=u'属性值的')
    required = fields.Boolean('Required', default=True)


class ProductCategory(models.Model):
    _inherit = 'product.category'

    no_create_variants = fields.Boolean(default=True, string=u"不自动创建规格产品", help='这个选项控制产品模板的属性设置是否自动创建变体')
    categ_attr_line_ids = fields.One2many('category.attribute.line', 'categ_id', u'属性配置')


    @api.onchange('no_create_variants')
    def onchange_no_create_variants(self):
        if not self.no_create_variants:
            return {'warning': {
                'title': _('Change warning!'),
                'message': _('Changing this parameter may cause'
                             ' automatic variants creation')
            }}

    @api.multi
    def write(self, values):
        res = super(ProductCategory, self).write(values)
        if ('no_create_variants' in values and
                not values.get('no_create_variants')):
            self.env['product.template'].search(
                [('categ_id', '=', self.id),
                 ('no_create_variants', '=', 'empty')]).create_variant_ids()
        return res
