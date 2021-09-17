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
    category = fields.Selection([
        ('default', 'Other'),('plan_check', u'计划检查'),('tb_date',u'出运相关日期')],
        string='Category',
        help='Categories may trigger specific behavior like opening calendar view')


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

    @api.depends('date_deadline','hegui_date','date_po_planned')
    def compute_date_deadline_hegui(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                time_supplier_requested = one.time_supplier_requested
                date_deadline = one.date_deadline and strptime(one.date_deadline, DF)
                hegui_date = one.hegui_date and strptime(one.hegui_date, DF)
                date_po_planned = one.date_po_planned and strptime(one.date_po_planned, DF)
                date_deadline_hegui = hegui_date and date_deadline and date_deadline - hegui_date
                date_deadline_planned = date_po_planned and date_deadline and  date_po_planned - date_deadline
                finish_percent_deadline = 0
                if time_supplier_requested and date_deadline:
                    finish_percent_deadline =  time_supplier_requested != 0 and date_deadline_hegui.days * 100 / time_supplier_requested or 0
                    if finish_percent_deadline >= 100:
                        finish_percent_deadline = 100
                print('')
                one.date_deadline_hegui = date_deadline_hegui.days
                one.date_deadline_planned = date_deadline_planned.days
                one.finish_percent_deadline = finish_percent_deadline

    # @api.depends('date_deadline')
    # def compute_date_deadline_hegui_store(self):
    #     for one in self:
    #         if one.type == 'order_track':
    #             strptime = datetime.strptime
    #             time_supplier_requested = one.time_supplier_requested
    #             date_deadline = one.date_deadline and strptime(one.date_deadline, DF)
    #             hegui_date = one.hegui_date and strptime(one.hegui_date, DF)
    #             date_deadline_hegui = hegui_date and date_deadline and date_deadline - hegui_date
    #             finish_percent_deadline = 0
    #             if time_supplier_requested and date_deadline:
    #                 finish_percent_deadline =  time_supplier_requested != 0 and date_deadline_hegui.days * 100 / time_supplier_requested or 0
    #                 if finish_percent_deadline >= 100:
    #                     finish_percent_deadline = 100
    #             # one.date_deadline_hegui = date_deadline_hegui.days
    #             # one.date_deadline_planned = date_deadline_planned.days
    #             one.finish_percent_deadline = finish_percent_deadline


    @api.depends('time_supplier_requested', 'hegui_date', 'date_po_planned')
    def compute_hegui_percent(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                today = datetime.today() - relativedelta(hours=-8)
                time_supplier_requested = one.time_supplier_requested  # 总的交期时间
                hegui_date = strptime(one.hegui_date, DF)
                date_po_planned = strptime(one.date_po_planned, DF)  # akiny带时间的转换
                if hegui_date and date_po_planned:
                    today_date_hegui = (today - hegui_date).days
                    today_date_plan = (today - date_po_planned).days
                    finish_percent_today_deadline = time_supplier_requested != 0 and today_date_hegui * 100 / time_supplier_requested or 0.0
                    print('finish_percent_today_deadline')
                    if finish_percent_today_deadline >= 100:
                        finish_percent_today_deadline = 100
                    one.finish_percent_today_deadline = finish_percent_today_deadline
                    one.today_date_hegui = today_date_hegui
                    one.today_date_plan = - today_date_plan


    @api.depends('po_id', 'po_id.date_planned',)
    def compute_date_po_planned_order(self):
        for one in self:
            one.date_po_planned = one.po_id.date_planned

    @api.depends('date_po_planned', 'hegui_date','date_deadline')
    def time_supplier_requested(self):
        for one in self:
            if one.date_po_planned and one.hegui_date:
                date_po_planned = datetime.strptime(one.date_po_planned,DF)
                hegui_date = datetime.strptime(one.hegui_date,DF)
                one.time_supplier_requested = (date_po_planned - hegui_date).days
            else:
                one.time_supplier_requested = 0

    @api.depends('order_track_id', 'order_track_id.partner_id', 'plan_check_line_id', 'po_id', 'po_id.source_so_id',
                 'po_id.source_so_id.partner_id','po_id.source_so_id.partner_id.assistant_id','po_id.source_so_id.partner_id.user_id')
    def compute_partner_id(self):
        for one in self:
            if one.order_track_id:
                partner_id = one.order_track_id.partner_id
            elif one.plan_check_line_id:
                partner_id = one.po_id.source_so_id.partner_id
            else:
                partner_id = False
            one.partner_id = partner_id
            one.assistant_id = partner_id.assistant_id
            one.sale_user_id = partner_id.user_id

    @api.depends('partner_id')
    def compute_assistant_user(self):
        for one in self:
            one.assistant_id = one.partner_id.assistant_id
            one.sale_user_id = one.partner_id.user_id



    partner_id = fields.Many2one('res.partner',compute=compute_partner_id,store=True)
    assistant_id = fields.Many2one('res.users','销售助理',compute=compute_assistant_user,store=True)
    sale_user_id = fields.Many2one('res.users','责任人',compute=compute_assistant_user,store=True)
    date_finish = fields.Date('完成时间')
    date_deadline_readonly = fields.Date('计划日期',related='date_deadline',readonly=1)
    plan_check_id = fields.Many2one('plan.check', '检查点', ondelete='cascade', )
    date_deadline = fields.Date('Due Date', index=True, required=False, )
    plan_check_line_id = fields.Many2one('plan.check.line', '检查点', ondelete='cascade', )
    po_id = fields.Many2one('purchase.order', '采购合同', related='plan_check_line_id.po_id', store=True)
    date_po_planned = fields.Date('工厂交期', compute=compute_date_po_planned_order, store=True)
    time_supplier_requested = fields.Integer('供应商交期时限', compute=time_supplier_requested, store=True)#交期-合规日期
    finish_percent_deadline = fields.Float('本计划在整个交期中的位置', compute=compute_date_deadline_hegui)  # 本计划所造总区间的位置，以及本计划在整个进度中的位置

    order_track_id = fields.Many2one('order.track', '活动计划', ondelete='cascade', )
    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track', '出运单跟踪')],
                            'type', related='order_track_id.type')
    hegui_date = fields.Date('合规审批时间',related='order_track_id.hegui_date')
    date_so_contract = fields.Date('客户下单日期', related='order_track_id.date_so_contract', store=True)
    date_so_requested = fields.Datetime('客户交期', related='order_track_id.date_so_requested', store=True)
    date_deadline_contract = fields.Integer('计划距合规日', )#compute=compute_date_deadline_contract
    date_deadline_requested = fields.Integer('计划距交期日', )#compute=compute_date_deadline_contract

    date_deadline_hegui = fields.Integer('计划距合规日', compute=compute_date_deadline_hegui)
    date_deadline_planned = fields.Integer('计划距交期日', compute=compute_date_deadline_hegui)

    today_date_so_contract = fields.Integer('今天距下单日', )#compute=compute_finish_percent
    today_date_so_requested = fields.Integer('今天距交期', )#compute=compute_finish_percent

    today_date_hegui = fields.Integer('今天距合规日', compute=compute_hegui_percent)
    today_date_plan = fields.Integer('今天距工厂交期', compute=compute_hegui_percent)
    finish_percent_today_deadline = fields.Float('完成期限比例', compute=compute_hegui_percent)#今日所造总区间的位置，以及本计划在整个进度中的位置


    finish_percent = fields.Float('完成期限比例', compute=compute_finish_percent)
    time_contract_requested = fields.Integer('总交期时间', related='order_track_id.time_contract_requested', store=True)

    def action_feedback(self, feedback=False):
        strptime = datetime.strptime
        strftime = datetime.strftime
        print('test1_akiny', str(self.date_finish), (datetime.today() - relativedelta(hours=-8)).strftime('%Y-%m-%d'))
        if self.date_finish and str(self.date_finish) > (datetime.today() - relativedelta(hours=-8)).strftime(
                '%Y-%m-%d'):
            raise Warning('完成日期不能大于当日')
        if not self.date_finish:
            raise Warning('完成日期还没有填写')
        if self.date_finish and self.hegui_date and self.date_finish < self.hegui_date:
            raise Warning('完成时间不能小于合规审批时间')

        if self.plan_check_line_id:
            self.plan_check_line_id.date_finish = self.date_finish  # akiny
        if self.order_track_id:
            if self.activity_type_id.name == '计划填写进仓日':
                if strptime(self.date_finish,DF).strftime('%Y-%m-01 00:00:00') <  fields.datetime.now().strftime('%Y-%m-01 00:00:00'):
                    raise Warning('进仓日期不允许小于单月')
                self.order_track_id.date_out_in = self.date_finish
                self.order_track_id.action_date_out_in()
                self.order_track_id.create_activity_plan_date_ship()
                self.order_track_id.create_activity_plan_date_customer_finish()

            elif self.activity_type_id.name == '计划填写船期':
                self.order_track_id.date_ship = self.date_finish
                self.order_track_id.tb_id.action_lock_stage()

                self.order_track_id.create_activity_plan_date_customer_finish()
            elif self.activity_type_id.name == '计划填写客户交单日':
                self.order_track_id.date_customer_finish = self.date_finish
            self.order_track_id.tb_id.compute_date_all_state()

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
        if self.date_finish and self.hegui_date and self.date_finish < self.hegui_date:
            raise Warning('完成时间不能小于合规审批时间')
        if self.date_finish and str(self.date_finish) > (datetime.today() - relativedelta(hours=-8)).strftime(
                '%Y-%m-%d'):
            raise Warning('完成日期不能大于当日')

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
                if self.date_deadline > self.date_so_requested or self.date_deadline > self.order_track_id.latest_date_po_planned:
                    print('ttst_akiny', self.date_deadline, self.date_so_requested,
                          self.date_deadline > self.date_so_requested)
                    raise Warning('计划时间不可以大于客户交期或者最迟供应商交期')

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
            if self.date_deadline > self.date_so_requested or self.date_deadline > self.order_track_id.latest_date_po_planned:
                print('ttst_akiny', self.date_deadline, self.date_so_requested,
                      self.date_deadline > self.date_so_requested)
                raise Warning('计划时间不可以大于客户交期或者最迟供应商交期')

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
