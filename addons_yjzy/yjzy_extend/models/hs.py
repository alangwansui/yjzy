# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, float_compare


class hs_hs(models.Model):
    _name = 'hs.hs'
    _description = 'HS编码'
    _rec_name = 'display_name'

    @api.depends('name','code')
    def compute_display_name(self):
        for one in self:
            one.display_name = '%s[%s]' % (one.name, one.code)

  #  @api.multi
   # def name_get(self):
   #     # 多选：only_name akiny
   #     result = []
   #     only_name = self.env.context.get('only_name')
   #     def _get_name(one):
   #         if only_name:
   #             name = '%s' % (one.name)
    #        else:
   #             name = '%s[%s]' % (one.name, one.code)

    #        return name

    #    for one in self:
    #        result.append((one.id, _get_name(one)))
   #     return result

    display_name = fields.Char(u'品名', compute=compute_display_name, store=True)
    name = fields.Char(u'中文品名')
    en_name = fields.Char(u'英文品名')
    code = fields.Char(u'编码')
    back_tax = fields.Float(u'退税率', digits=dp.get_precision('Back Tax'))

    # _sql_constraints = [
    #     ('unique_name', 'unique(name)', "HS品名中文名称不允许重复"),
    # ]


