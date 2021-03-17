# -*- coding: utf-8 -*-

from odoo import models, fields, api


class wizard_plan_check_comments(models.TransientModel):
    _name = 'wizard.plan.check.comments'

    comments = fields.Text('备注日志', )
    order_track_id = fields.Many2one('order.track',)
    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track', '出运单跟踪')],
                            'type')

    def apply(self):
        if self.type == 'new_order_track':
            self.order_track_id.write({
                'comments_new_order_track':self.comments
            })
        elif self.type == 'order_track':
            self.order_track_id.write({
                'comments_order_track':self.comments
            })
        else:
            self.order_track_id.write({
                'comments_transport_track':self.comments
            })
