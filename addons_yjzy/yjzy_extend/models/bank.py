# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from . comm import sfk_type
import logging
from odoo.osv import expression

class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    @api.depends('acc_number')
    def compute_display_name(self):
        for one in self:
            ctx = self.env.context.get('display_name_code')
            if ctx:
                display_name = '%s\n%s\n%s' % (one.huming, one.acc_number, one.kaihuhang)
                one.display_name = display_name
                print('display_name', one.display_name)
            else:
                one.display_name = '%s' % (one.acc_number)

    huming = fields.Char(u'收款人')
    kaihuhang = fields.Char(u'开户行')
    bank_type = fields.Selection([('company_supplier', '供应商'), ('personal', '用户个人')], '内部类型')
    huming_address = fields.Char(u'收款人地址')
    swift = fields.Char('SWIFT(非中国大陆供应商)')
    kaihuhang_address = fields.Char('银行地址')
    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    @api.multi
    def name_get(self):
        res = []
        for one in self:
            fullname = '%s:%s:%s' % (one.huming, one.acc_number, one.kaihuhang)
            res.append((one.id, fullname))
        return res

    @api.model
    def name_search(self, name, args=None, operator='ilike', limit=100):
        args = args or []
        domain = []
        if name:
            domain = ['|', ('huming', '=ilike', name + '%'), ('acc_number', operator, name)]
            if operator in expression.NEGATIVE_TERM_OPERATORS:
                domain = ['&'] + domain
        banks = self.search(domain + args, limit=limit)
        return banks.name_get()
