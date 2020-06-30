# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp

#13完成
class packaging_type(models.Model):
    _name = 'packaging.type'

    @api.depends('height', 'width', 'length')
    def compute_volume(self):
        for one in self:
            one.volume = one.height * one.width * one.length

    name = fields.Char(u'名称', required=True, translate=True)
    height = fields.Float(u'高cm')
    width = fields.Float(u'宽cm')
    length = fields.Float(u'长cm')
    volume = fields.Float(u'体积cm³', compute=compute_volume, store=True)
    weight = fields.Float(u'重量')
    size = fields.Selection([(1, u'大'), (2, u'中'), (3, u'小')], u'型号', default=1)
    thick = fields.Float(u'厚度')

    max_default = fields.Boolean(u'默认大包装')
    min_default = fields.Boolean(u'默认小包装')


    @api.constrains('height', 'width', 'length')
    def check_size(self):
        if self.height < 0:
            raise Warning(u'高必须大于0')
        if self.width < 0:
            raise Warning(u'宽必须大于0')
        if self.length < 0:
            raise Warning(u'长必须大于0')


class product_packaging(models.Model):
    _inherit = 'product.packaging'

    @api.depends('height', 'width', 'length2')
    def compute_volume(self):
        for one in self:
            one.volume = one.height * one.width * one.length

    length2 = fields.Float(u'长度cm')  # 这个字段onchange不生效
    length = fields.Float(u'长度cm', related='length2')
    height = fields.Float(u'高cm')
    width = fields.Float(u'宽cm')
    type_id = fields.Many2one('packaging.type', u'包装类型', required=False)
    packaging_weight = fields.Float(u'包装重量', related='type_id.weight', readonly=False)
    net_weight = fields.Float(u'净重', readonly=False, digits=dp.get_precision('Stock Weight'),)
    volume = fields.Float(u'体积cm³', compute=compute_volume, store=True)
    size = fields.Selection([(1, u'大'), (2, u'中'), (3, u'小')], u'型号', default=1)
    weight4product = fields.Float(u'包含产品的重量', digits=dp.get_precision('Stock Weight'),)
    thick = fields.Float(u'厚度')

    @api.onchange('type_id')
    def onchange_pachage_type(self):
        self.height = self.type_id.height
        self.width = self.type_id.width
        self.length2 = self.type_id.length
        self.volume = self.type_id.volume
        self.name = self.type_id.name
        self.size = self.type_id.size
