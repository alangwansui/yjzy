# -*- coding: utf-8 -*-

from odoo import models, fields, api

class product_product(models.Model):
    _inherit = 'product.product'

    length = fields.Float(string=u'长')
    width = fields.Float(string=u'宽')
    height = fields.Float(string=u'高')
    # dimensions_uom_id = fields.Many2one( 'product.uom', '尺寸(UOM)',
    #                                      domain = lambda self:[('category_id','=',self.env.ref('product.uom_categ_length').id)],
    #                                      default = default_dimensions_uom )

    @api.onchange('length', 'width', 'height')
    def onchange_size(self):
        #print ('============================================================================')
        self.volume = self.length * self.width * self.height



