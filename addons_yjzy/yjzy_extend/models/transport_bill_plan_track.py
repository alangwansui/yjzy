# -*- coding: utf-8 -*-
from num2words import num2words
from odoo import models, fields, api, _
from odoo.exceptions import Warning
from . comm import BACK_TAX_RATIO

class transport_bill(models.Model):
    _inherit = 'transport.bill'

    order_track_ids = fields.One2many('order.track','tb_id', domain=[('type', '=', 'transport_track')])
    plan_check_ids = fields.One2many('plan.check','tb_id',domain=[('order_track_id.type','=','transport_track')])




    # 创建第一步新订单检验
    def make_new_order_track_tb(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])

        if not self.order_track_ids:
            order_track_transport_track = order_track_obj.create({
                'type': 'transport_track',
                'tb_id':self.id,
            })
            order_track_transport_track.create_plan()









