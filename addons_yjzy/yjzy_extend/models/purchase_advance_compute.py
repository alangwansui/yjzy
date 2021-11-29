# -*- coding: utf-8 -*-
import math

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import Warning, UserError
from odoo.osv import expression
from odoo.addons.purchase.models.purchase import PurchaseOrder

Stage_Status_Default = 'draft'

Purchase_Selection = [('draft', '草稿'),
                      ('sent', 'RFQ Sent'),
                      ('submit', u'带责任人审批'),
                      ('sales_approve', u'待产品经理审批'),
                      ('approve', '待出运'),  # akiny 翻译成等待出运
                      ('purchase', '开始出运'),
                      ('abnormal', '异常核销'),
                      ('verifying', '正常核销'),
                      ('done', '核销完成'),
                      ('cancel', '取消'),
                      ('refused', u'已拒绝'),

                      ]
Sale_Selection = [('draft', '草稿'),
                  ('cancel', '取消'),
                  ('refused', u'拒绝'),
                  ('submit', u'待责任人审核'),
                  ('sales_approve', u'待业务合规审核'),
                  ('manager_approval', u'待总经理特批'),
                  ('approve', u'审批完成待出运'),
                  ('sale', '开始出运'),
                  ('abnormal', u'异常核销'),
                  ('verifying', u'正常核销'),
                  ('verification', u'核销完成'), ]


class purchase_order(models.Model):
    _inherit = 'purchase.order'

    @api.depends('yjzy_payment_ids', 'yjzy_payment_ids.prepayment_type', 'yjzy_payment_ids.amount')
    def compute_real_advance_new(self):
        for one in self:
            yjzy_payment_ids = one.yjzy_payment_ids.filtered(lambda x: x.prepayment_type != 'before_delivery')
            if one.yjzy_payment_ids:
                real_advance_new = sum([x.amount for x in yjzy_payment_ids])
            else:
                real_advance_new = 0
            one.real_advance_new = real_advance_new

    @api.depends('yjzy_payment_ids', 'yjzy_payment_ids.prepayment_type', 'yjzy_payment_ids.amount')
    def compute_real_advance_before_delivery_new(self):
        for one in self:

            yjzy_payment_ids = one.yjzy_payment_ids.filtered(lambda x: x.prepayment_type == 'before_delivery')
            if one.yjzy_payment_ids:
                real_advance_before_delivery_new = sum([x.amount for x in yjzy_payment_ids])
            else:
                real_advance_before_delivery_new = 0
            one.real_advance_before_delivery_new = real_advance_before_delivery_new

    real_advance_new = fields.Monetary(u'实际预付金额', compute='compute_real_advance_new', currency_field='yjzy_currency_id',
                                       )
    real_advance_before_delivery_new = fields.Monetary(u'实际发货前金额', compute='compute_real_advance_before_delivery_new',
                                                       currency_field='yjzy_currency_id',
                                                       )
    real_advance_all = fields.Monetary(u'总预付金额', compute='compute_real_advance_all')

    def compute_real_advance_all(self):
        for one in self:
            real_advance_new = one.real_advance_new
            real_advance_before_delivery_new = one.real_advance_before_delivery_new
            one.real_advance_all = real_advance_new + real_advance_before_delivery_new

###############################
