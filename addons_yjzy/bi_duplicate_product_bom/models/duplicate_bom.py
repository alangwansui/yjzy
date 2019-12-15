# -*- coding: utf-8 -*-
# Part of BrowseInfo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models, _, tools

class DuplicateProduct(models.Model):
    _inherit = 'product.template'
    
    def copy(self, default=None):
        if default is None:
            default = {}
        duplicate_id = super(DuplicateProduct, self).copy()
        product_bom_obj = self.env['mrp.bom'].search([('product_tmpl_id.id','=', self.id)])
        for bom_id in product_bom_obj:
            bom_id.copy({'product_tmpl_id': duplicate_id.id})
        return duplicate_id

class DuplicateProductVariant(models.Model):
    _inherit = 'product.product'
    
    def copy(self, default=None):
        if default is None:
            default = {}
        duplicate_id = super(DuplicateProductVariant, self).copy(default=default)
        product_bom_obj = self.env['mrp.bom'].search([('product_id.id','=', self.id)])
        for bom_id in product_bom_obj:
            bom_id.copy({'product_id': duplicate_id.id})
        return duplicate_id



# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:           
