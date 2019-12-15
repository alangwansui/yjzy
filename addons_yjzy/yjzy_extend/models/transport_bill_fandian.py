# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO

class transport_bill_fandian(models.Model):
    _name = 'transport.bill.fandian'


    tb_id = fields.Many2one('transport.bill', u'出运单')

    name = fields.Char('Name')
    supplier_id = fields.Many2one('res.partner', u'供应商')
    partner_id = fields.Many2one('res.partner', u'返点对象')
    purchase_amout = fields.Float(u'采购金额')
    fandian_amount = fields.Float(u'返点金额')

    #
    # 返点明细：供应商，返点对象，采购金额，。公式：如果含税：采购金额 *（1 - 增值税率0
    # .13）*返点比例，如果不含税：采购金额 * 返点比例

