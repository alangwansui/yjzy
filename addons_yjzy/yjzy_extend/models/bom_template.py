# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class bom_template(models.Model):
    _name = 'bom.template'
    _description = u'BOM模板'

    name = fields.Char(u'Name', required=True)
    product_template = fields.Many2one('product.template', u'产品')
    line_ids = fields.One2many('bom.template.line', 'bom_template_id', u'明细')

class bom_template_line(models.Model):
    _name = 'bom.template.line'

    bom_template_id = fields.Many2one('bom.template', 'BOM模板')
    product_tmpl_id = fields.Many2one('product.template', u'产品', required=True)
    product_id = fields.Many2one('product.product', u'产品规格', domain="[('product_tmpl_id', '=', product_tmpl_id)]")
    qty = fields.Float(u'数量')


