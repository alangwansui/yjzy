# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import Warning, UserError
from odoo.tools import float_is_zero, float_compare
from . comm import sfk_type
import logging


class res_partner_bank(models.Model):
    _inherit = 'res.partner.bank'

    huming = fields.Char(u'户名')
    kaihuhang = fields.Char(u'开户行')

    @api.multi
    def name_get(self):
        res = []
        for one in self:
            fullname = '%s:%s:%s' % (one.huming, one.acc_number, one.kaihuhang)
            res.append((one.id, fullname))
        return res
