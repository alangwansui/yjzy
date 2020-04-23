# -*- coding: utf-8 -*-

from odoo import api, fields, models



#akiny 客户目前经营的产品类目
class partner_product_origin(models.Model):
    _name = 'partner.product.origin'
    _description = '联系人产品'



    name = fields.Char(u'名称', required=True)
    description = fields.Text('产品描述')
    partner_id = fields.Many2one('res.partner','联系人')

