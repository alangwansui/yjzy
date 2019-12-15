# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
class Product_Attribute_Value(models.Model):
    _inherit = 'product.attribute.value'
    _order = 'attribute_id'

    attribute_group_id = fields.Many2one(related='attribute_id.attribute_group_id', readonly=True)


class Product_Attribute(models.Model):
    _inherit = 'product.attribute'
    _order = 'sequence,attribute_group_id'

    @api.depends('seq', 'attribute_group_id', 'attribute_group_id.sequence')
    def compute_sequence(self):
        for one in self:
            one.sequence = one.attribute_group_id.sequence * 1000 + one.seq

    attribute_group_id = fields.Many2one('attribute.group', u'属性组')
    sequence = fields.Integer('总排序', index=True, compute=compute_sequence, store=True)
    sequence2 = fields.Integer('排序', related='sequence')
    seq = fields.Integer('排序', index=True, default=1)


class Attribute_Group(models.Model):
    _name = 'attribute.group'
    _order = 'sequence'

    name = fields.Char(u'属性组', required=True)
    attribute_ids = fields.One2many('product.attribute', 'attribute_group_id', u'产品属性')
    sequence = fields.Integer('排序', default=1)
    sequence2 = fields.Integer('排序', related='sequence', readonly=1)



class product_attribute_rel(models.Model):
    """
    delete from product_attribute_value_product_product_rel;
    alter table product_attribute_value_product_product_rel add id serial;
    create sequence product_attribute_value_product_product_rel_id_seq;
    alter table product_attribute_value_product_product_rel alter column id set default nextval('product_attribute_value_product_product_rel_id_seq'::regclass)；
    """
    _name = 'product.value.rel'
    _table = 'product_attribute_value_product_product_rel'
    _rec_name = 'product_attribute_value_id'
    _order = 'attribute_group_id,attribute_id'
    _description = u'产品属性明细'

    # def compute_name(self):
    #     for one in self:
    #         one.name = '%s:%s' % (one.product_attribute_value_id.attribute_id.name, one.product_attribute_value_id.name)

    id = fields.Id('ID')
    #name = fields.Char('Name', compute=compute_name, store=True)
    product_product_id = fields.Many2one('product.product', u'产品', required=True,  ondelete='restrict')
    product_attribute_value_id = fields.Many2one('product.attribute.value', u'属性值', required=False)

    is_key = fields.Boolean(u'是关键')
    attribute_id = fields.Many2one('product.attribute', u'属性')
    attribute_group_id = fields.Many2one('attribute.group', related='attribute_id.attribute_group_id', store=True)

    @api.multi
    def update_attribute_by_value(self):
        for one in self:
            if not one.attribute_id:
                one.attribute_id = one.product_attribute_value_id.attribute_id

    @api.onchange('attribute_id')
    def onchange_attribute(self):
        if self.attribute_id != self.product_attribute_value_id.attribute_id:
            self.product_attribute_value_id = None









