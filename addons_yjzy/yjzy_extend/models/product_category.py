# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models

class Product_Catgory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(u'类别编码', size=2)
    complete_name2 = fields.Char(u'全称', compute='_compute_complete_name2')
    #hs_id = fields.Many2one('hs.hs', u'品名')
    #hs_code = fields.Char(u"HS编码")
    #back_tax = fields.Float(u'退税率')
    #hs_name = fields.Char(u'报关品名', translate=True)
    #bom_template_id = fields.Many2one('bom.template', 'BOM模板')

    @api.depends('name', 'parent_id.complete_name2')
    def _compute_complete_name2(self):
        for category in self:
            if category.parent_id:
                category.complete_name2 = '%s / %s' % (category.parent_id.complete_name2, category.name)
            else:
                category.complete_name2 = category.name


    # def get_hs_code(self):
    #     self.ensure_one()
    #     if self.hs_code:
    #         return self.hs_code
    #     else:
    #         return self.parent_id.hs_code

    # def get_hs_name(self):
    #     self.ensure_one()
    #     if self.hs_name:
    #         return self.hs_name
    #     else:
    #         return self.parent_id.hs_name

    # def get_back_tax(self):
    #     self.ensure_one()
    #     if self.back_tax:
    #         return self.back_tax
    #     else:
    #         return self.parent_id.back_tax