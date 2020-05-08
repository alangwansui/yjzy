# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from . comm import sfk_type
import logging


class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    huming = fields.Char(u'收款人')
    kaihuhang = fields.Char(u'开户行')
    bank_type = fields.Selection([('company_supplier', '供应商'), ('personal', '用户个人')], '内部类型')
    huming_address = fields.Char(u'收款人地址')
    swift = fields.Char('SWIFT(非中国大陆供应商)')
    kaihuhang_address = fields.Char('银行地址')
    @api.multi
    def name_get(self):
        res = []
        for one in self:
            fullname = '%s:%s:%s' % (one.huming, one.acc_number, one.kaihuhang)
            res.append((one.id, fullname))
        return res
