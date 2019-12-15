# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning

class ProductImage(models.Model):
    _inherit = 'product.image'

    product_id = fields.Many2one('product.product', u'产品', copy=True)