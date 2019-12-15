# -*- coding: utf-8 -*-

from odoo import models, fields, api
import logging
_logger = logging.getLogger(__name__)

class wizard_product_copy(models.TransientModel):
    _name = 'wizard.product.copy'
    _description = u'产品复制向导'

    line_ids = fields.One2many('wizard.product.copy.line', 'wizard_id', u'Lines')
    product_id = fields.Many2one('product.product', u'产品')

    def apply(self):
        _logger.info('====================wizard_product_copy======================start')
        product = self.product_id
        value = {'attribute_value_ids': [(6, 0, [x.value_id.id for x in self.line_ids])]}
        new_product = product.copy(default=value)

        _logger.info('====================wizard_product_copy======================end')
        return {
            'name': u'复制产品',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'product.product',
            'res_id': new_product.id,
            # 'target': 'new',
            'type': 'ir.actions.act_window',
        }

    @api.model
    def create(self, values):
        wizard = super(wizard_product_copy, self).create(values)
        line_obj = self.env['wizard.product.copy.line']
        for v in wizard.product_id.attribute_value_ids:
            line_obj.create({
                'wizard_id': wizard.id,
                'attribute_id': v.attribute_id.id,
                'value_id': v.id,
            })
        return wizard


class wizard_product_copy_line(models.TransientModel):
    _name = 'wizard.product.copy.line'
    _order = 'attribute_id,value_id'

    wizard_id = fields.Many2one('wizard.product.copy', u'wizard')
    attribute_id = fields.Many2one('product.attribute', u'属性', index=True)
    value_id = fields.Many2one('product.attribute.value', u'属性')
    attribute_group_id = fields.Many2one('attribute.group', related='attribute_id.attribute_group_id', string=u'属性组')
