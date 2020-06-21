# -*- coding: utf-8 -*-

from odoo import api, fields, models



#akiny 客户目前经营的产品类目
class partner_product_origin(models.Model):
    _name = 'partner.product.origin'
    _description = 'Partner Product'



    name = fields.Char('Name', required=True)
    description = fields.Text('Description')
    partner_id = fields.Many2one('res.partner','Partner')

