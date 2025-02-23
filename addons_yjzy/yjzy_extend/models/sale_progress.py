# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from .comm import BACK_TAX_RATIO
from odoo.exceptions import Warning
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from datetime import datetime
from dateutil.relativedelta import relativedelta


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    @api.depends('po_source_ids', 'po_source_ids.date_factory_return')
    def compute_po_return_state(self):
        for one in self:
            po_ids = one.po_source_ids
            po_return_ids = po_ids.filtered(lambda x: x.date_factory_return == False)
            if len(po_ids) == len(po_return_ids):
                po_return_state = 'un_return'
            elif len(po_ids) != len(po_return_ids) and len(po_return_ids) > 0:
                po_return_state = 'part_return'
            else:
                po_return_state = 'returned'
            one.po_return_state = po_return_state

    time_receive_pi = fields.Date('收到客户订单时间')
    time_sent_pi = fields.Date('发送PI时间')
    time_sign_pi = fields.Date('客户PI回签时间')
    time_receive_po = fields.One2many('purchase.order', 'source_so_id', '工厂回传时间')
    plan_check_ids = fields.One2many('plan.check', 'so_id')
    order_track_ids = fields.One2many('order.track', 'so_id')

    po_return_state = fields.Selection([('un_return', '未回传'), ('part_return', '部分回传'), ('returned', '已回传')],
                                       '工厂回传状态', default='un_return', compute=compute_po_return_state, store=True)

    @api.onchange('time_receive_pi', 'time_sent_pi', 'contract_date')
    def onchange_time_receive_pi(self):
        strptime = datetime.strptime
        print('time_akiny', self.time_receive_pi, self.time_sent_pi)
        if self.time_receive_pi and self.time_sent_pi:
            if self.time_receive_pi > self.time_sent_pi:
                raise Warning('填写的日期顺序不正确，请检查1!')
        if self.time_receive_pi and self.contract_date:
            if self.time_receive_pi > self.contract_date:
                raise Warning('填写的日期顺序不正确，请检查2!')
        if self.time_sent_pi and self.contract_date:
            if self.time_sent_pi > self.contract_date:
                raise Warning('填写的日期顺序不正确，请检查3!')
        if self.time_receive_pi and strptime(self.time_receive_pi, DF) > datetime.today() - relativedelta(hours=-8):
            raise Warning('客户订单号不可大于当日')
        if self.time_sent_pi and strptime(self.time_sent_pi, DF) > datetime.today() - relativedelta(hours=-8):
            raise Warning('发送PI不可大于当日')
        if self.contract_date and strptime(self.contract_date, DF) > datetime.today() - relativedelta(hours=-8):
            raise Warning('客户确认日期大于当日')

    # 合规审批完成创建订单跟踪
    # todo 创建的时候执行了一次，合规审批完又是一次？查找原因：合规审批真理不需要整个执行，而是需要计算一下compute_order_track_state()就可以，
    #  todo 将状态变成日期填制完成，后面还有一个供应商回传，状态变化后，就会进入订单跟踪流程
    def make_all_plan(self):
        self.make_new_order_track()
        self.make_plan_check_new()

    # 创建第二步订单检查
    def make_plan_check(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])
        res_model_id = models_obj.search([('model', '=', 'plan.check')])

        if not self.order_track_ids.filtered(lambda x: x.type == 'order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)
            order_track_new_order_track = order_track_obj.create({
                'type': 'order_track',
                'so_id': self.id,
                'po_ids': [(6, 0, po_dic)],
                'time_draft_order': self.create_date,
                'planning_integrity': '10_un_planning',
                'check_on_time': '10_not_time',
            })

            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type': 'order_track',
                    'so_id': self.id,
                    'po_id': one.id,
                    'order_track_id': order_track_new_order_track.id,
                    'state': 'planning'

                })

                ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
                alarm_dic = []
                for alarm in ba_activity_deadline_alarm:
                    alarm_dic.append(alarm.id)
                for x in activity_type_akiny_ids:
                    plan_check_line = plan_check_line_obj.create({
                        'plan_check_id': plan_check.id,
                        'activity_type_1_id': x.id,
                        'state': 'planning',
                        'order_track_id': order_track_new_order_track.id
                    })
                    plan_check_line_activity = activity_obj.create({
                        'activity_type_id': x.id,
                        'user_id': self.env.user.id,
                        'plan_check_id': plan_check.id,
                        'plan_check_line_id': plan_check_line.id,
                        'activity_category': 'plan_check',
                        'res_model': 'plan.check',
                        'res_model_id': res_model_id.id,
                        'res_id': plan_check.id,
                        'reminder_ids': [(6, 0, alarm_dic)],

                    })
                    plan_check_line.write({'activity_id': plan_check_line_activity.id})

    # 创建活动直接到没一条plan.check.line
    def make_plan_check_new(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])
        res_model_id = models_obj.search([('model', '=', 'plan.check.line')])
        ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
        alarm_dic = []
        for alarm in ba_activity_deadline_alarm:
            alarm_dic.append(alarm.id)
        if not self.order_track_ids.filtered(lambda x: x.type == 'order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)
            order_track_new_order_track = order_track_obj.create({
                'type': 'order_track',
                'so_id': self.id,
                'po_ids': [(6, 0, po_dic)],
                'time_draft_order': self.create_date,
            })

            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type': 'order_track',
                    'so_id': self.id,
                    'po_id': one.id,
                    'order_track_id': order_track_new_order_track.id,
                    'state': 'planning',

                })
                sequence = 1
                for x in activity_type_akiny_ids:
                    plan_check_line = plan_check_line_obj.create({
                        'plan_check_id': plan_check.id,
                        'activity_type_1_id': x.id,
                        'po_id': one.id,
                        'sequence': sequence,
                        'state': '10_un_planning',
                        'order_track_id': order_track_new_order_track.id
                    })
                    sequence += 1
                    plan_check_line_activity = activity_obj.create({
                        'activity_type_id': x.id,
                        'user_id': self.env.user.id,
                        'assistant_id': self.env.user.id,
                        'sale_user_id': self.env.user.assistant_id.id,
                        'order_track_id': order_track_new_order_track.id,
                        'plan_check_id': plan_check.id,
                        'plan_check_line_id': plan_check_line.id,
                        'activity_category': 'plan_check',
                        'res_model': 'plan.check.line',
                        'res_model_id': res_model_id.id,
                        'res_id': plan_check_line.id,
                        'reminder_ids': [(6, 0, alarm_dic)],
                    })
                    plan_check_line.write({'activity_id': plan_check_line_activity.id})
        else:
            if not self.plan_check_ids.filtered(lambda x: x.type == 'order_track'):
                order_track_ids = self.order_track_ids.filtered(lambda x: x.type == 'order_track')
                po_dic = []
                for line in self.po_ids:
                    po_dic.append(line.id)
                order_track_ids[0].write({
                    'po_ids': [(6, 0, po_dic)],
                })
                print('akiny_test', po_dic, self.po_ids, order_track_ids)
                for one in self.po_ids:
                    plan_check = plan_check_obj.create({
                        'type': 'order_track',
                        'so_id': self.id,
                        'po_id': one.id,
                        'order_track_id': order_track_ids[0].id,
                        'state': 'planning'
                    })
                    sequence = 1
                    for x in activity_type_akiny_ids:
                        plan_check_line = plan_check_line_obj.create({
                            'plan_check_id': plan_check.id,
                            'activity_type_1_id': x.id,
                            'po_id': one.id,
                            'sequence': sequence,
                            'state': '10_un_planning',
                            'order_track_id': order_track_ids[0].id
                        })
                        sequence += 1
                        plan_check_line_activity = activity_obj.create({
                            'activity_type_id': x.id,
                            'user_id': self.env.user.id,
                            'assistant_id': self.env.user.id,
                            'sale_user_id': self.env.user.assistant_id.id,
                            'order_track_id': order_track_ids[0].id,
                            'plan_check_id': plan_check.id,
                            'plan_check_line_id': plan_check_line.id,
                            'activity_category': 'plan_check',
                            'res_model': 'plan.check.line',
                            'res_model_id': res_model_id.id,
                            'res_id': plan_check_line.id,
                            'reminder_ids': [(6, 0, alarm_dic)],
                        })
                        plan_check_line.write({'activity_id': plan_check_line_activity.id})

    # 创建第一步新订单检验
    def make_new_order_track(self):
        order_track_obj = self.env['order.track']
        plan_check_obj = self.env['plan.check']
        plan_check_line_obj = self.env['plan.check.line']
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        activity_type_akiny_ids = type_obj.search([('category', '=', 'plan_check')])
        ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
        alarm_dic = []
        for alarm in ba_activity_deadline_alarm:
            alarm_dic.append(alarm.id)
        if not self.order_track_ids.filtered(lambda x: x.type == 'new_order_track'):
            po_dic = []
            for line in self.po_ids:
                po_dic.append(line.id)
            order_track_new_order_track = order_track_obj.create({
                'type': 'new_order_track',
                'so_id': self.id,
                'po_ids': [(6, 0, po_dic)],
                'time_draft_order': self.create_date,
                'hegui_date': self.approve_date,

            })
            self.plan_check_ids.unlink()
            for one in self.po_ids:
                plan_check = plan_check_obj.create({
                    'type': 'new_order_track',
                    'so_id': self.id,
                    'po_id': one.id,
                    'order_track_id': order_track_new_order_track.id,

                })
            order_track_new_order_track.compute_order_track_state()
        else:
            if not self.plan_check_ids.filtered(lambda x: x.type == 'new_order_track'):
                self.plan_check_ids.unlink()
                order_track_ids = self.order_track_ids.filtered(lambda x: x.type == 'new_order_track')
                po_dic = []
                for line in self.po_ids:
                    po_dic.append(line.id)
                order_track_ids[0].write({
                    'po_ids': [(6, 0, po_dic)],
                })
                print('akiny_test', po_dic, self.po_ids, order_track_ids)
                for one in self.po_ids:
                    plan_check = plan_check_obj.create({
                        'type': 'new_order_track',
                        'so_id': self.id,
                        'po_id': one.id,
                        'order_track_id': order_track_ids[0].id,

                    })
            self.order_track_ids.compute_order_track_state()
