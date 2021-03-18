# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from . comm import BACK_TAX_RATIO

class sale_order(models.Model):
    _inherit = 'sale.order'




    time_receive_pi = fields.Date('收到客户订单时间')
    time_sent_pi = fields.Date('发送PI时间')
    time_sign_pi = fields.Date('客户PI回签时间')
    time_receive_po = fields.One2many('purchase.order','source_so_id','工厂回传时间')

    plan_check_ids = fields.One2many('plan.check','so_id')
    order_track_ids = fields.One2many('order.track','so_id')





    # def make_activity_akiny_ids(self):
    #     res = []
    #     type_obj = self.env['mail.activity.type']
    #     activity_obj = self.env['mail.activity']
    #     activity_type_akiny_ids = type_obj.search([('category','=', 'plan_check')])
    #     print('activity_akiny_ids_akiny',activity_type_akiny_ids)
    #
    #     if self.activity_akiny_ids:
    #         self.activity_akiny_ids.unlink()
    #     for one in activity_type_akiny_ids:
    #         activity_akiny_ids = activity_obj.create({
    #             'activity_type_id':one.id,
    #             'user_id':self.env.user.id,
    #             'so_id':self.id,
    #             'activity_category':'plan_check',
    #             'res_model':'sale.order',
    #             'res_model_id':260,
    #             'res_id':self.id,
    #
    #         })

    def make_all_plan(self):
        self.make_new_order_track()
        self.make_plan_check_new()

    #创建第二步订单检查
    def make_plan_check(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])
        res_model_id = models_obj.search([('model','=','plan.check')])

        if not self.order_track_ids.filtered(lambda x: x.type == 'order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)
            order_track_new_order_track = order_track_obj.create({
                'type':'order_track',
                'so_id':self.id,
                'po_ids':[(6, 0, po_dic)],
                'time_draft_order':self.create_date,
                'planning_integrity':'10_un_planning',
                'check_on_time': '10_not_time',
            })

            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type':'factory_check',
                    'so_id':self.id,
                    'po_id':one.id,
                    'order_track_id':order_track_new_order_track.id,
                    'state':'planning'


                })
                for x in activity_type_akiny_ids:
                    plan_check_line = plan_check_line_obj.create({
                        'plan_check_id':plan_check.id,
                        'activity_type_1_id':x.id,
                        'state':'planning',
                        'order_track_id': order_track_new_order_track.id
                    })
                    plan_check_line_activity = activity_obj.create({
                    'activity_type_id': x.id,
                    'user_id': self.env.user.id,
                    'plan_check_id': plan_check.id,
                    'plan_check_line_id':plan_check_line.id,
                    'activity_category': 'plan_check',
                    'res_model': 'plan.check',
                    'res_model_id': res_model_id.id,
                    'res_id': plan_check.id,
                })
                    plan_check_line.write({'activity_id':plan_check_line_activity.id})

    #创建活动直接到没一条plan.check.line
    def make_plan_check_new(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])
        res_model_id = models_obj.search([('model','=','plan.check.line')])

        if not self.order_track_ids.filtered(lambda x: x.type == 'order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)
            order_track_new_order_track = order_track_obj.create({
                'type':'order_track',
                'so_id':self.id,
                'po_ids':[(6, 0, po_dic)],
                'time_draft_order':self.create_date,
            })

            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type':'factory_check',
                    'so_id':self.id,
                    'po_id':one.id,
                    'order_track_id':order_track_new_order_track.id,
                    'state':'planning'


                })
                for x in activity_type_akiny_ids:
                    plan_check_line = plan_check_line_obj.create({
                        'plan_check_id':plan_check.id,
                        'activity_type_1_id':x.id,
                        'state':'10_un_planning',
                        'order_track_id': order_track_new_order_track.id
                    })
                    plan_check_line_activity = activity_obj.create({
                    'activity_type_id': x.id,
                    'user_id': self.env.user.id,
                    'plan_check_id': plan_check.id,
                    'plan_check_line_id':plan_check_line.id,
                    'activity_category': 'plan_check',
                    'res_model': 'plan.check.line',
                    'res_model_id': res_model_id.id,
                    'res_id': plan_check_line.id,
                })
                    plan_check_line.write({'activity_id':plan_check_line_activity.id})


    #创建第一步新订单检验
    def make_new_order_track(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])

        if not self.order_track_ids.filtered(lambda x: x.type == 'new_order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)

            order_track_new_order_track = order_track_obj.create({
                'type': 'new_order_track',
                'so_id': self.id,
                'po_ids': [(6, 0, po_dic)],
                'time_draft_order': self.create_date,
                'hegui_date':self.approve_date,
            })
            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type': 'factory_check',
                    'so_id': self.id,
                    'po_id': one.id,
                    'order_track_id': order_track_new_order_track.id,

                })





