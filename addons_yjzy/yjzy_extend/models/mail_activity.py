# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from datetime import date, datetime, timedelta
import pytz
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DT

from odoo.exceptions import Warning, UserError
from odoo import api, exceptions, fields, models, _
from dateutil.relativedelta import relativedelta


class MailActivityType(models.Model):
    """ Activity Types are used to categorize activities. Each type is a different
    kind of activity e.g. call, mail, meeting. An activity can be generic i.e.
    available for all models using activities; or specific to a model in which
    case res_model_id field should be used. """
    _inherit = 'mail.activity.type'
    category = fields.Selection(selection_add=[('plan_check', '计划检查')])


class MailActivity(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _inherit = 'mail.activity'

    @api.depends('time_contract_requested', 'date_so_contract', 'date_so_requested')
    def compute_finish_percent(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                today = datetime.today() - relativedelta(hours=-8)
                time_contract_requested = one.time_contract_requested
                date_so_contract = strptime(one.date_so_contract, DF)
                date_so_requested = strptime(str(one.date_so_requested), '%Y-%m-%d 00:00:00')  # akiny带时间的转换
                print('date_so_requested', date_so_requested, )
                if date_so_contract and time_contract_requested:
                    today_date_so_contract = (today - date_so_contract).days
                    today_date_so_requested = (today - date_so_requested).days
                    print('x_akiny', date_so_contract, today, date_so_requested, today_date_so_requested)
                    finish_percent = time_contract_requested != 0 and today_date_so_contract * 100 / time_contract_requested or 0
                    if finish_percent >= 100:
                        finish_percent = 100
                    one.finish_percent = finish_percent
                    one.today_date_so_contract = - today_date_so_contract
                    one.today_date_so_requested = - today_date_so_requested

                    print('finish_percent_akiny', finish_percent)

    @api.depends('date_deadline')
    def compute_date_deadline_contract(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                date_deadline = strptime(one.date_deadline, DF)
                date_so_contract = one.date_so_contract and strptime(one.date_so_contract, DF)
                date_so_requested = one.date_so_requested and strptime(str(one.date_so_requested), '%Y-%m-%d 00:00:00')

                date_deadline_contract = date_so_contract and date_so_contract - date_deadline
                date_deadline_requested = date_so_requested and date_so_requested - date_deadline
                one.date_deadline_contract = date_deadline_contract and date_deadline_contract.days
                one.date_deadline_requested = date_deadline_contract and date_deadline_requested.days

    date_finish = fields.Date('完成时间')

    plan_check_id = fields.Many2one('plan.check', '检查点', ondelete='cascade', )
    date_deadline = fields.Date('Due Date', index=True, required=False, )
    plan_check_line_id = fields.Many2one('plan.check.line', '检查点', ondelete='cascade', )
    po_id = fields.Many2one('purchase.order', '采购合同', related='plan_check_line_id.po_id', store=True)
    order_track_id = fields.Many2one('order.track', '活动计划', ondelete='cascade', )
    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track', '出运单跟踪')],
                            'type', related='order_track_id.type')

    date_so_contract = fields.Date('客户下单日期', related='order_track_id.date_so_contract', store=True)
    date_so_requested = fields.Datetime('客户交期', related='order_track_id.date_so_requested', store=True)
    date_deadline_contract = fields.Integer('计划距下单日', compute=compute_date_deadline_contract)
    date_deadline_requested = fields.Integer('计划距交期日', compute=compute_date_deadline_contract)

    today_date_so_contract = fields.Integer('今天距下单日', compute=compute_finish_percent)
    today_date_so_requested = fields.Integer('今天距交期', compute=compute_finish_percent)
    finish_percent = fields.Float('完成期限比例', compute=compute_finish_percent)
    time_contract_requested = fields.Integer('总交期时间', related='order_track_id.time_contract_requested', store=True)

    def action_feedback(self, feedback=False):
        strptime = datetime.strptime
        print('test1_akiny', str(self.date_finish), (datetime.today() - relativedelta(hours=-8)).strftime('%Y-%m-%d'))
        if self.date_finish and str(self.date_finish) > (datetime.today() - relativedelta(hours=-8)).strftime(
                '%Y-%m-%d'):
            raise Warning('完成日期不能大于当日')
        plan_check_line_obj = self.env['plan.check.line']
        plan_check_line_ids = plan_check_line_obj.search([('po_id', '=', self.po_id.id)])
        print('finish_akiny_1', plan_check_line_ids)
        for one in plan_check_line_ids:
            if not self.date_finish:
                raise Warning('完成时间不能小于下单给供应商时间,请重新选择时间')
            if self.date_finish and one.date_order:
                if self.date_finish and one.date_order:
                    date_order = one.date_order and strptime(one.date_order, DT).date()
                    print('finish_akiny_1', strptime(self.date_finish, DF).date(), date_order)
                    if strptime(self.date_finish, DF).date() < date_order:
                        raise Warning('完成时间不能小于下单给供应商时间')

        if self.plan_check_line_id:
            self.plan_check_line_id.date_finish = self.date_finish  # akiny
        if self.order_track_id:
            if self.activity_type_id.name == '计划填写进仓日':
                self.order_track_id.date_out_in = self.date_finish
                self.order_track_id.create_activity_plan_date_ship()
                self.order_track_id.create_activity_plan_date_customer_finish()
            elif self.activity_type_id.name == '计划填写船期':
                self.order_track_id.date_ship = self.date_finish
                self.order_track_id.create_activity_plan_date_customer_finish()
            elif self.activity_type_id.name == '计划填写客户交单日':
                self.order_track_id.date_customer_finish = self.date_finish

        message = self.env['mail.message']
        if feedback:
            self.write(dict(feedback=feedback))
        for activity in self:
            record = self.env[activity.res_model].browse(activity.res_id)
            record.message_post_with_view(
                'mail.message_activity_done',
                values={'activity': activity},
                subtype_id=self.env.ref('mail.mt_activities').id,
                mail_activity_type_id=activity.activity_type_id.id,
            )
            message |= record.message_ids[0]

        self.unlink()
        return message.ids and message.ids[0] or False

    @api.onchange('date_finish')
    def onchange_date_finish(self):
        strptime = datetime.strptime
        strftime = datetime.strftime
        plan_check_line_obj = self.env['plan.check.line']
        plan_check_line_ids = plan_check_line_obj.search([('po_id', '=', self.po_id.id)])
        print('finish_akiny', plan_check_line_ids)
        for one in plan_check_line_ids:
            if self.date_finish and one.date_order:
                date_order = one.date_order and strptime(one.date_order, DT).date()
                print('finish_akiny_1', strptime(self.date_finish, DF).date(), date_order)
                if strptime(self.date_finish, DF).date() < date_order:
                    raise Warning('完成时间不能小于下单给供应商时间')

    @api.onchange('dd')
    def onchange_dd(self):
        strptime = datetime.strptime
        if self.type == 'order_track':
            date_deadline = datetime.strptime(self.dd, DT) - relativedelta(hours=-8)
            self.date_deadline = date_deadline
            print('date_deadline', date_deadline, self.dd, datetime.strptime(self.dd, DT))
            if self.date_deadline and str(self.date_deadline) < (datetime.today() - relativedelta(hours=-8)).strftime(
                    '%Y-%m-%d'):  # 参考str时间也可以比较

                print('dd_akiny', str(self.date_deadline),
                      (datetime.today() - relativedelta(hours=-8)).strftime('%Y-%m-%d'))
                raise Warning('计划日期不能小于今天')
            activity_type_obj = self.env['mail.activity.type']
            plan_check_line_obj = self.env['plan.check.line']
            activity_obj = self.env['mail.activity']
            activity_ids = activity_obj.search([('po_id', '=', self.po_id.id)])
            plan_check_line_ids = plan_check_line_obj.search([('po_id', '=', self.po_id.id)])
            print('activity_ids_akiny_1', plan_check_line_ids)
            if self.date_deadline:
                if self.date_deadline > self.date_so_requested:
                    print('ttst_akiny', self.date_deadline, self.date_so_requested,
                          self.date_deadline > self.date_so_requested)
                    raise Warning('计划时间不可以大于客户交期')

            for one in plan_check_line_ids:
                print('activity_ids_akiny', one.sequence,
                      one.date_deadline, self.date_deadline)
                if one.date_deadline:
                    if one.sequence < self.plan_check_line_id.sequence and one.date_deadline > self.date_deadline:
                        raise Warning('计划时间要按顺序')
                    if one.sequence > self.plan_check_line_id.sequence and one.date_deadline < self.date_deadline:
                        raise Warning('计划时间要按顺序')
                # if self.date_deadline and one.date_order:
                #     date_order = one.date_order and strptime(one.date_order, DT).date()
                #     print('finish_akiny_1', strptime(self.date_deadline, DF).date(), date_order)
                #     if strptime(self.date_deadline, DF).date() < date_order:
                #         raise Warning('计划时间不能小于下单给供应商时间')

    @api.multi
    def action_close_dialog(self):
        strptime = datetime.strptime
        if self.type == 'order_track':
            date_deadline = datetime.strptime(self.dd, DT) - relativedelta(hours=-8)
            self.date_deadline = date_deadline
            if self.date_deadline and str(self.date_deadline) < (datetime.today() - relativedelta(hours=-8)).strftime(
                    '%Y-%m-%d'):  # 参考str时间也可以比较
                raise Warning('计划日期不能小于今天')
            activity_type_obj = self.env['mail.activity.type']
            plan_check_line_obj = self.env['plan.check.line']
            activity_obj = self.env['mail.activity']
            activity_ids = activity_obj.search([('po_id', '=', self.po_id.id)])
            plan_check_line_ids = plan_check_line_obj.search([('po_id', '=', self.po_id.id)])
            print('activity_ids_akiny_1', plan_check_line_ids)
            if self.date_deadline > self.date_so_requested:
                raise Warning('计划时间不可以大于客户交期')

            for one in plan_check_line_ids:
                print('activity_ids_akiny', one.sequence,
                      one.date_deadline, self.date_deadline)
                if one.date_deadline:
                    if one.sequence < self.plan_check_line_id.sequence and one.date_deadline > self.date_deadline:
                        raise Warning('计划时间要按顺序')
                    if one.sequence > self.plan_check_line_id.sequence and one.date_deadline < self.date_deadline:
                        raise Warning('计划时间要按顺序')
                # if self.date_deadline and one.date_order:
                #     date_order = one.date_order and strptime(one.date_order, DT).date()
                #     print('finish_akiny_1', strptime(self.date_deadline, DF).date(), date_order)
                #     if strptime(self.date_deadline, DF).date() < date_order:
                #         raise Warning('计划时间不能小于下单给供应商时间')

        if self.plan_check_line_id:
            self.plan_check_line_id.date_deadline = self.date_deadline
        return {'type': 'ir.actions.act_window_close'}

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}
