# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, fields, models
from .budget_budget import Budget_Type_Selection

class Product_Catgory(models.Model):
    _inherit = 'product.category'

    code = fields.Char(u'类别编码', size=2)
    complete_name2 = fields.Char(u'全称', compute='_compute_complete_name2')
    sequence = fields.Integer('排序')
    #hs_id = fields.Many2one('hs.hs', u'品名')
    #hs_code = fields.Char(u"HS编码")
    #back_tax = fields.Float(u'退税率')
    #hs_name = fields.Char(u'报关品名', translate=True)
    #bom_template_id = fields.Many2one('bom.template', 'BOM模板')

    is_user_budget = fields.Boolean(u'作用人员预算')
    is_company_budget = fields.Boolean(u'公司预算')

    budget_type = fields.Selection(Budget_Type_Selection, '预算类型')


    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        ctx = self.env.context
        if ctx.get('search_order'):
            recs = self.search([('name', operator, name)] + (args or []), limit=limit, order=ctx.get('search_order'))
            return recs.name_get()
        return super(Product_Catgory, self).name_search(name, args=args, operator=operator, limit=limit)



    @api.depends('name', 'parent_id.complete_name2')
    def _compute_complete_name2(self):
        for category in self:
            if category.parent_id:
                category.complete_name2 = '%s / %s' % (category.parent_id.complete_name2, category.name)
            else:
                category.complete_name2 = category.name

    @api.multi
    def name_get(self):
        # 多选：only_name akiny
        result = []
        only_name = self.env.context.get('only_name')

        def _get_name(one):
            if not only_name:
                name = one.complete_name2
            else:
                name = one.name

            return name

        for one in self:
            result.append((one.id, _get_name(one)))
        return result

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