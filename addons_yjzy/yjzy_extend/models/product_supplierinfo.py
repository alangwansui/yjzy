# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class product_supplierinfo(models.Model):
    _inherit = 'product.supplierinfo'
    _rec_name = 'full_name'
    _order = 'id desc,sequence, min_qty desc, price'

    @api.depends('name', 'product_name', 'product_code')
    def compute_full_name(self):
        for one in self:
            one.full_name = '%s:%s:%s' % (one.name.name, one.product_code or '', one.product_name or '')

    #13已经添加
    full_name = fields.Char(u'全称', compute=compute_full_name, store=True)
    product_customer_id = fields.Many2one('res.partner',related='product_id.customer_id',store=True)
    product_customer_ref = fields.Char('客户编号',related='product_id.customer_ref',store=True)

    # def  name_get(self):
    #     res = super(product_supplierinfo, self).name_get
    #
    #     return res

