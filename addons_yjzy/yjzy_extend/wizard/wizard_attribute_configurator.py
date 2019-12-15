# -*- coding: utf-8 -*-

from odoo import models, fields, api


class wizard_attribute_configurator(models.TransientModel):
    _name = 'wizard.attribute.configurator'

    name = fields.Char(u'属性组', required=False)
    type = fields.Selection([('add', u'增加'), ('over', u'覆盖')], u'方式', default='over', readonly=True)
    attribute_group_id = fields.Many2one('attribute.group', u'属性组')
    line_ids = fields.One2many('wizard.attribute.configurator.line', 'wizard_id', u'明细')
    product_id = fields.Many2one('product.product', u'产品')

    @api.onchange('attribute_group_id')
    def onchange_attribute_group(self):
        line_obj = self.env['wizard.attribute.configurator.line']
        lines = self.env['wizard.attribute.configurator.line'].browse([])
        for attr in self.attribute_group_id.attribute_ids:
            line = line_obj.create({
                'wizard_id': self._origin.id,
                'attribute_id': attr.id,
            })
            lines |= line
        self.line_ids = lines


    def apply(self):
        self.ensure_one()
        product = self.product_id
        values = self.line_ids.mapped('value_id')
        # if self.type == 'add':
        #     values |= product.attribute_value_ids
        product.attribute_value_ids = values


class wizard_attribute_configurator_line(models.TransientModel):
    _name = 'wizard.attribute.configurator.line'
    _order = 'attribute_id,value_id'

    wizard_id = fields.Many2one('wizard.attribute.configurator', u'wizard')
    attribute_id = fields.Many2one('product.attribute', u'属性', index=True)
    value_id = fields.Many2one('product.attribute.value', u'值', index=True)
    attribute_group_id = fields.Many2one('attribute.group', related='attribute_id.attribute_group_id', string=u'属性组')
