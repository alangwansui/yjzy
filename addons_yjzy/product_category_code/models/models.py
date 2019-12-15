# -*- coding: utf-8 -*-

from odoo import models, fields, api


class product_category(models.Model):
    _inherit = 'product.category'
    #_parent_store = False   #分类数据导入完成后，重新计算左右值
    _order = 'complete_code'

    @api.multi
    @api.depends('parent_id', 'code')
    def _compute_level(self):
        for category in self:
            level = 0
            if category.parent_id:
                level = category.parent_id.level + 1
            category.level = level

    @api.multi
    @api.depends('parent_id', 'code')
    def _compute_complete_code(self):
        res = {}
        for categ in self:
            code = categ.code or ''
            parent_complete_code = categ.parent_id and categ.parent_id.complete_code
            if parent_complete_code:
                code = '%s%s' % (parent_complete_code, code)
            categ.complete_code = code

    level = fields.Integer(compute=_compute_level, string=u'级别', store=True, type='integer')
    code = fields.Char(u'编码', size=2, required=False, default='')
    complete_code = fields.Char(compute=_compute_complete_code, string=u'完整编码', type='char', store=True)

    # _sql_constraints = [
    #     ('uniq_code_parent', 'unique(parent_id,code)', u'不能有相同的 上级和编码'),
    # ]

    def recalculate_level(self):
        all_categories = self.search([], order='id')
        for categ in all_categories:
            level = 0
            if categ.parent_id:
                level = categ.parent_id.level + 1
            categ.level = level
        return True

    @api.constrains('level', 'code')
    def check_code_width(self):
        dic = self.env['ir.config_parameter'].get_param('product_category_code.product_category_level_width')
        dic = dic and eval(dic)
        if dic:
            if dic.get(self.level) and dic.get(self.level) != len(self.code):
                raise Warning(u'分类等级%s,编码[%s]长度不是%s' % (self.level, self.code, dic.get(self.level)))


    @api.multi
    def check_ok(self):
        pass



###########################################################################
