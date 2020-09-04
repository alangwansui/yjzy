# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
import logging
_logger = logging.getLogger(__name__)

class Product_Template(models.Model):
    _inherit = 'product.template'

    #13不要
    def compute_tmpl_code(self):
        for one in self:
            one.tmpl_code = str(one.id).rjust(6, '0')

    @api.depends('product_variant_ids', 'product_variant_ids.hs_id')
    def _compute_hs_id(self):
        unique_variants = self.filtered(lambda template: len(template.product_variant_ids) == 1)
        for template in unique_variants:
            template.hs_id = template.product_variant_ids.hs_id
        for template in (self - unique_variants):
            template.hs_id = None

    @api.one
    def _set_hs_id(self):
        if len(self.product_variant_ids) == 1:
            self.product_variant_ids.hs_id = self.hs_id


    en_name = fields.Char(u'英文名')
    hs_id = fields.Many2one('hs.hs', string='HS品名', compute='_compute_hs_id',
                            inverse='_set_hs_id', store=True)
    back_tax = fields.Float(related='hs_id.back_tax', readonly=True)
    hs_en_name = fields.Char(related='hs_id.en_name', readonly=True)
    customer_ref = fields.Char(u'客户型号', related='product_variant_ids.customer_ref')

    tmpl_code = fields.Char(u'模板编码', required=False, compute=compute_tmpl_code)

    need_print = fields.Boolean('是否打印', default=True) #13已
    need_split_bom = fields.Boolean(u'需要展开BOM')#13已

    is_gold_sample = fields.Boolean('是否有金样')


    tracking = fields.Selection([
        ('serial', 'By Unique Serial Number'),
        ('lot', 'By Lots'),
        ('none', 'No Tracking')], string="Tracking", default='lot', required=True)


    # @api.onchange('categ_id')
    # def onchange_category(self):
    #     self.hs_id = self.categ_id.hs_id






