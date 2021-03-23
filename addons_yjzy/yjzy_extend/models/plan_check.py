# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, timedelta,date
from dateutil.relativedelta import relativedelta
from odoo.exceptions import Warning, UserError

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
class OrderTrackCategory(models.Model):

    _name = "order.track.category"
    _description = "check Category"

    name = fields.Char(string="Check Tag", required=True)
    color = fields.Integer(string='Color Index')
    order_track_ids = fields.Many2many('order.track', 'order_track_category_rel', 'category_id', 'track_id', string='Check')
    _sql_constraints = [
        ('name_uniq', 'unique (name)', "Tag name already exists !"),
    ]

class OrderTrack(models.Model):
    _name = 'order.track'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = '计划跟踪'

    @api.depends('plan_check_ids','plan_check_ids.date_po_order')
    def compute_earliest_date_po_order(self):
        for one in self:
            date_po_orders = one.plan_check_ids.filtered(lambda x: x.date_po_order != False)
            if len(date_po_orders) == 0:
                earliest_date_po_order = False
            else:
                earliest_date_po_order = min(date_po_orders.mapped('date_po_order'))
            one.earliest_date_po_order = earliest_date_po_order

    @api.depends('plan_check_ids', 'plan_check_ids.date_po_planned')
    def compute_latest_date_po_planned(self):
        for one in self:
            date_po_planned = one.plan_check_ids.filtered(lambda x: x.date_po_planned != False)
            if len(date_po_planned) == 0:
                latest_date_po_planned = False
            else:
                latest_date_po_planned = max(date_po_planned.mapped('date_po_planned'))
            one.latest_date_po_planned = latest_date_po_planned

    @api.depends('date_so_requested','date_so_contract')
    def compute_time_contract_requested(self):
        strptime = datetime.strptime
        strftime = datetime.strptime
        for one in self:
            if one.date_so_requested and one.date_so_contract:
                time = '00:00:00'
                date_so_requested = "%s" % (strftime(one.date_so_requested,'%Y-%m-%d 00:00:00'))
                date_so_contract = "%s" % (strftime(one.date_so_contract,'%Y-%m-%d'))
                print('date_so_contract_akiny',date_so_contract,date_so_requested)
                print('akiny_1', strptime(date_so_requested, DATETIME_FORMAT))
                time_contract_requested = (strptime(date_so_requested, DATETIME_FORMAT) - strptime(date_so_contract, DATETIME_FORMAT)).days
                print('akiny_2', time_contract_requested)
            else:
                time_contract_requested = 0

            one.time_contract_requested = time_contract_requested

    @api.depends('earliest_date_po_order', 'latest_date_po_planned')
    def compute_time_supplier_requested(self):
        strptime = datetime.strptime
        strftime = datetime.strptime
        for one in self:
            if one.earliest_date_po_order and one.latest_date_po_planned:
                time = '00:00:00'
                earliest_date_po_order = one.earliest_date_po_order
                latest_date_po_planned = one.latest_date_po_planned

                time_supplier_requested = (
                            strptime(latest_date_po_planned, DF) - strptime(earliest_date_po_order, DF)).days
                print('akiny_2', time_supplier_requested)
            else:
                time_supplier_requested = 0

            one.time_supplier_requested = time_supplier_requested

    def compute_finish_percent(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                today = datetime.today()
                time_contract_requested = one.time_contract_requested
                date_so_contract = one.date_so_contract
                if date_so_contract and time_contract_requested:
                    x = (today - strptime(one.date_so_contract , DF)).days
                    print('x_akiny',x,time_contract_requested)
                    finish_percent = time_contract_requested != 0 and x * 100 / time_contract_requested or 0
                    if finish_percent >= 100:
                        finish_percent = 100
                    one.finish_percent = finish_percent


    def compute_finish_percent_supplier(self):
        for one in self:
            if one.type == 'order_track':
                strptime = datetime.strptime
                today = datetime.today()
                time_supplier_requested = one.time_supplier_requested
                earliest_date_po_order = one.earliest_date_po_order
                print('earliest_date_po_order_ainy',earliest_date_po_order)
                if time_supplier_requested and earliest_date_po_order:
                    x = (today - strptime(earliest_date_po_order, DF)).days
                    finish_percent_supplier = time_supplier_requested != 0 and x * 100 / time_supplier_requested or 0.0
                    if finish_percent_supplier >=100:
                        finish_percent_supplier = 100
                    one.finish_percent_supplier = finish_percent_supplier

    @api.depends('plan_check_ids','plan_check_ids.plan_check_line')
    def compute_check_all_number(self):
        len_number = 0
        for one in self:
            if one.plan_check_ids:
                len_number = len(one.plan_check_ids) * len(one.plan_check_ids[0].plan_check_line)
            one.check_all_number = len_number

    @api.depends('plan_check_ids', 'plan_check_ids.plan_check_line', 'plan_check_ids.plan_check_line.state')
    def compute_check_finish_number_old(self):
        for one in self:
            num = 0
            for line in one.plan_check_ids:
                if line.plan_check_line:
                    for x in line.plan_check_line:
                        if x.state in ['finish', 'time_out_finish']:
                            num += 1
            one.check_finish_number = num

    @api.depends('plan_check_line_ids','plan_check_line_ids.state')
    def compute_check_finish_number(self):
        for one in self:
            num = 0
            for x in one.plan_check_line_ids:
                if x.state in ['finish', 'time_out_finish']:
                    num += 1
            one.check_finish_number = num

    def compute_check_number_percent(self):
        for one in self:
            check_number_percent = one.check_all_number !=0 and  one.check_finish_number * 100 / one.check_all_number or 0.0
            one.check_number_percent = check_number_percent

    def compute_display_name(self):
        ctx = self.env.context
        for one in self:
            if one.type in ['new_order_track','order_track']:
                display_name = '%s' % (one.so_id.contract_code)
            else:
                display_name = '%s' % (one.tb_id.ref)
            one.display_name = display_name



    @api.depends('so_id', 'so_id.sent_qty', 'so_id.no_sent_qty', 'so_id.all_qty')
    def compute_so_qty(self):
        for one in self:
            if one.type == 'order_track':
                so_id = one.so_id
                so_sent_qty = so_id.sent_qty
                so_no_sent_qty = so_id.no_sent_qty
                so_all_qty = so_id.all_qty

                one.so_sent_qty = so_sent_qty
                one.so_no_sent_qty = so_no_sent_qty
                one.so_all_qty = so_all_qty
                one.sent_percent = so_all_qty != 0 and (so_sent_qty / so_all_qty) * 100 or 0.0

    @api.depends('tb_purchase_invoice_ids','tb_purchase_invoice_ids.currency_id')
    def compute_purchase_back_invoice_currency_id(self):
        for one in self:
            if one.tb_purchase_invoice_ids:
                one.purchase_back_invoice_currency_id = one.tb_purchase_invoice_ids[0].currency_id
            else:
                one.purchase_back_invoice_currency_id = self.env.user.company_id.currency_id

    @api.depends('so_id', 'tb_id', 'so_id.company_id', 'tb_id.company_id')
    def compute_company_id(self):
        for one in self:
            if one.type in ['new_order_track', 'order_track']:
                company_id = one.so_id.company_id
            else:
                company_id = one.tb_id.company_id
            one.company_id = company_id

    def compute_order_track_state(self):
        for one in self:
            if one.time_draft_order and one.time_sign_pi and one.time_sent_pi and one.time_receive_pi and one.hegui_date and len(one.plan_check_ids) == len(one.plan_check_ids.filtered(lambda x: x.date_factory_return != False)):
                one.order_track_new_order_state = '20_done'
            else:
                one.order_track_new_order_state = '10_doing'

    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('order.track'))
    category_ids = fields.Many2many(
        'order.track.category','order_track_category_rel',  'track_id','category_id',
        string='Tags',store=True)

    order_track_new_order_state = fields.Selection([('10_doing','跟踪进行时候'),('20_done','已完成')],'下单前状态',compute=compute_order_track_state,defautl='10_doing',store=True)


    sale_state_1 = fields.Selection(Sale_Selection, u'审批流程', related='so_id.state_1',store=True
                              )  # 费用审批流程
    planning_integrity = fields.Selection([('10_un_planning','未计划'),('20_part_un_planning','部分未计划'),('30_planning','已完全计划')],
                                          u'计划安排完整性',default='10_un_planning')
    check_on_time = fields.Selection([('10_not_time',u'未到时'),('20_out_time_un_finish',u'超时未完成'),('30_on_time_finish',u'准时完成'),('40_out_time_finish',u'超时完成')],
                                     u'检查执行准时性',default='10_not_time')

    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track','出运单跟踪')], 'type')
    so_id = fields.Many2one('sale.order', '销售合同' ,ondelete='cascade')
    partner_id = fields.Many2one('res.partner','客户',related='so_id.partner_id',store=True)
    so_sent_qty = fields.Float('已出运数',compute=compute_so_qty,store=True)

    so_all_qty = fields.Float('原始总数',compute=compute_so_qty,store=True)
    so_no_sent_qty = fields.Float('未出运数',compute=compute_so_qty,store=True)
    sent_percent = fields.Float('出运进度',compute='compute_so_qty',store=True)

    tb_id = fields.Many2one('transport.bill', '出运合同' ,ondelete='cascade')
    tb_purchase_invoice_ids = fields.One2many('account.invoice','order_track_id','应付账单',domain=[('yjzy_type','=','purchase')])
    purchase_back_invoice_currency_id =fields.Many2one('res.currency',compute=compute_purchase_back_invoice_currency_id,store=True)
    sale_invoice_currency_id =fields.Many2one('res.currency',related='tb_id.sale_currency_id')

    tb_sale_invoice_id = fields.One2many('account.invoice','order_track_id',domain=[('yjzy_type','=','sale')])
    sale_invoice_balance = fields.Monetary('应收款',currency_field='sale_invoice_currency_id',related='tb_id.sale_invoice_balance_new',store=True)
    purchase_invoice_balance = fields.Monetary('应付款',currency_field='purchase_back_invoice_currency_id',related='tb_id.purchase_invoice_balance_new',store=True)
    back_tax_invoice_balance = fields.Monetary('应收退税',currency_field='purchase_back_invoice_currency_id',related='tb_id.back_tax_invoice_balance_new',store=True)
    date_all_state = fields.Selection([('10_date_approving',u'日期审批中'),
                                       ('20_no_date_out_in',u'发货日期待填'),
                                       ('30_un_done',u'其他日期待填'),
                                       ('40_done',u'已完成相关日期'),
                                       ],'所有日期状态',related='tb_id.date_all_state',store=True, )

    date_out_in = fields.Date('进仓日期',related='tb_id.date_out_in',store=True)
    plan_date_out_in = fields.Date('计划进仓日')
    plan_date_out_in_activity = fields.Many2one('mail.activity', '进仓日计划活动')
    is_date_out_in = fields.Boolean('进仓日是否已确认',related='tb_id.is_date_out_in',store=True)
    date_in = fields.Date('入库日期',related='tb_id.date_in',store=True)
    date_ship = fields.Date('出运船日期',related='tb_id.date_ship',store=True)
    approve_date = fields.Date('审批完成时间',related='tb_id.approve_date',store=True)
    plan_date_ship = fields.Date('计划出运船日',)
    plan_date_ship_activity = fields.Many2one('mail.activity', '出运船计划活动')
    # activity_ids = fields.One2many('mail.activity','order_track_id','计划活动')





    date_customer_finish = fields.Date('客户交单日期',related='tb_id.date_customer_finish')
    plan_date_customer_finish = fields.Date('计划客户交单日', )
    plan_date_customer_finish_activity = fields.Many2one('mail.activity', '客户交单计划活动')

    date_supplier_finish = fields.Date('最迟供应商交单确认日期')



    po_ids = fields.Many2many('purchase.order','ref_pp', 'fid', 'tid','采购单')
    company_id = fields.Many2one('res.company', '公司', compute=compute_company_id,store=True)




    time_draft_order = fields.Datetime('so_create_date',related='so_id.create_date',store=True)
    hegui_date = fields.Date('合规审批时间',track_visibility='onchange',related='so_id.approve_date',store=True)
    time_receive_pi = fields.Date('收到客户订单时间',track_visibility='onchange',related='so_id.time_receive_pi',store=True)
    time_sent_pi = fields.Date('发送PI时间',track_visibility='onchange',related='so_id.time_sent_pi',store=True)
    time_sign_pi = fields.Date('客户PI回签时间',track_visibility='onchange',related='so_id.contract_date',store=True)

    date_so_contract = fields.Date('客户下单日期',related='so_id.contract_date',store=True)
    date_so_requested = fields.Datetime('客户交期',related='so_id.requested_date',store=True)

    time_contract_requested = fields.Integer('客户交期时限',compute=compute_time_contract_requested,store=True)
    finish_percent = fields.Float('完成期限比例',compute=compute_finish_percent,store=True)


    earliest_date_po_order = fields.Date('最早供应商下单时间',compute=compute_earliest_date_po_order,store=True)
    latest_date_po_planned = fields.Date('最迟供应商交单时间',compute=compute_latest_date_po_planned,store=True)

    time_supplier_requested = fields.Integer('供应商交期时限', compute=compute_time_supplier_requested, store=True)
    finish_percent_supplier = fields.Float('供应商完成期限比例', compute=compute_finish_percent_supplier,store=True)
    #供应商总的分步检查数量
    check_all_number = fields.Integer('供应商总分步检查数',compute=compute_check_all_number,store=True)
    check_finish_number = fields.Integer('供应商完成分步检查数',compute=compute_check_finish_number, store =True)
    check_number_percent = fields.Float('分步完成比例',compute=compute_check_number_percent,store=True)

    plan_check_ids = fields.One2many('plan.check','order_track_id','计划跟踪明细')
    factory_return = fields.One2many('plan.check','order_track_id','工厂回签日期',)
    plan_check_line_ids = fields.One2many('plan.check.line','order_track_id','计划跟踪详情')

    comments_new_order_track = fields.Text('备注日志',track_visibility='onchange')
    comments_order_track = fields.Text('备注日志', track_visibility='onchange')
    comments_transport_track = fields.Text('备注日志', track_visibility='onchange')

    @api.onchange('plan_check_line_ids','plan_check_line_ids.date_deadline','plan_check_line_ids.date_deadline')
    def onchange_plan_check_line_ids(self):
        for one in self.onchange_plan_check_line_ids:
            if one.date_deadline < one.po_id.date_order:
                raise Warning('计划检查点时间不允许小于供应商下单时间')
            if one.date_deadline > one.po_id.date_planned:
                raise Warning('计划检查点时间不允许大于供应商交期')

    @api.onchange('plan_check_ids')
    def onchange_plan_check_ids(self):
        for one in self.plan_check_ids:
            if one.date_factory_return and one.date_factory_return < self.time_sign_pi:
                raise Warning('工厂回签时间小于客户PI回签时间')




    @api.onchange('time_receive_pi')
    def onchange_time_receive_pi(self):
        print('time_akiiny',self.time_receive_pi,self.time_sent_pi)
        if self.time_receive_pi and self.time_sent_pi:
            if self.time_receive_pi > self.time_sent_pi:
                raise Warning('填写的日期顺序不正确，请检查!')
        if self.time_receive_pi and self.time_sign_pi:
            if self.time_receive_pi > self.time_sign_pi:
                raise Warning('填写的日期顺序不正确，请检查!')

    @api.onchange('time_sign_pi')
    def onchange_time_sign_pi(self):
        print('time_akiiny', self.time_receive_pi, self.time_sent_pi)
        if self.time_receive_pi and self.time_sent_pi:
            if self.time_receive_pi > self.time_sent_pi:
                raise Warning('填写的日期顺序不正确，请检查!')
        if self.time_sent_pi and self.time_sign_pi:
            if self.time_sent_pi > self.time_sign_pi:
                raise Warning('填写的日期顺序不正确，请检查!')

    @api.onchange('time_sent_pi')
    def onchange_time_sent_pi(self):
        print('time_akiiny', self.time_receive_pi, self.time_sent_pi)
        if self.time_receive_pi and self.time_sign_pi:
            if self.time_receive_pi > self.time_sign_pi:
                raise Warning('填写的日期顺序不正确，请检查!')
        if self.time_sent_pi and self.time_sign_pi:
            if self.time_sent_pi > self.time_sign_pi:
                raise Warning('填写的日期顺序不正确，请检查!')


    def create_plan(self):
        self.create_activity_plan_date_out_in()
        self.create_activity_plan_date_ship()
        self.create_activity_plan_date_customer_finish()

    def create_activity_plan_date_out_in(self):
        strptime = datetime.strptime
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('name', '=', '计划填写进仓日')], limit=1)
        res_model_id = models_obj.search([('model', '=', 'order.track')])
        approve_date = datetime.strptime(str(self.approve_date),'%Y-%m-%d')
        plan_date = approve_date + relativedelta(days=+7)  # 参考时间akiny
        print('approve_date_1_akuny', approve_date, approve_date, plan_date)
        ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
        alarm_dic = []
        for alarm in ba_activity_deadline_alarm:
            alarm_dic.append(alarm.id)

        plan_check_line_activity = activity_obj.create({
            'activity_type_id': activity_type_akiny_ids[0].id,
            'user_id': self.env.user.id,
            'activity_category': 'default',
            'res_model': 'order.track',
            'res_model_id': res_model_id.id,
            'res_id': self.id,
            'dd': plan_date,
            'order_track_id':self.id,
            'reminder_ids': [(6, 0, alarm_dic)],
        })
        self.plan_date_out_in = plan_date
        self.write({
            'plan_date_out_in_activity':plan_check_line_activity.id
        })


    def create_activity_plan_date_ship(self):
        strptime = datetime.strptime
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('name', '=', '计划填写船期')], limit=1)
        res_model_id = models_obj.search([('model', '=', 'order.track')])
        ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
        alarm_dic = []
        for alarm in ba_activity_deadline_alarm:
            alarm_dic.append(alarm.id)
        if self.date_out_in:
            date_out_in = datetime.strptime(str(self.date_out_in), '%Y-%m-%d')
            plan_date = date_out_in + relativedelta(days=+7)  # 参考时间akiny
        elif self.plan_date_out_in:
            date_out_in = datetime.strptime(str(self.plan_date_out_in), '%Y-%m-%d')
            plan_date = date_out_in + relativedelta(days=+7)  # 参考时间akiny
        else:
            return True
        if not self.plan_date_ship_activity:
            plan_check_line_activity = activity_obj.create({
                'activity_type_id': activity_type_akiny_ids[0].id,
                'user_id': self.env.user.id,
                'activity_category': 'default',
                'res_model': 'order.track',
                'res_model_id': res_model_id.id,
                'res_id': self.id,
                'dd': plan_date,
                'order_track_id': self.id,
                'reminder_ids': [(6, 0, alarm_dic)],
            })
            self.plan_date_ship = plan_date
            self.write({
                'plan_date_ship_activity': plan_check_line_activity.id
            })
        else:
            print('plan_date_akiny',plan_date)
            self.plan_date_ship_activity.write({
                'dd': plan_date,
                'reminder_ids': [(6, 0, alarm_dic)],
            })
            self.plan_date_ship = plan_date


    def create_activity_plan_date_customer_finish(self):
        strptime = datetime.strptime
        type_obj = self.env['mail.activity.type']
        activity_obj = self.env['mail.activity']
        models_obj = self.env['ir.model']
        activity_type_akiny_ids = type_obj.search([('name', '=', '计划填写客户交单日')], limit=1)
        res_model_id = models_obj.search([('model', '=', 'order.track')])
        ba_activity_deadline_alarm = self.env['ba_activity_deadline.alarm'].search([])
        alarm_dic = []
        for alarm in ba_activity_deadline_alarm:
            alarm_dic.append(alarm.id)
        if self.date_ship:
            date_ship = datetime.strptime(str(self.date_ship), '%Y-%m-%d')
            plan_date = date_ship + relativedelta(days=+7)  # 参考时间akiny
        elif self.plan_date_ship:
            plan_date_ship = datetime.strptime(str(self.plan_date_ship), '%Y-%m-%d')
            plan_date = plan_date_ship + relativedelta(days=+7)  # 参考时间akiny
        else:
            return True
        if not self.plan_date_customer_finish_activity:
            plan_check_line_activity = activity_obj.create({
                'activity_type_id': activity_type_akiny_ids[0].id,
                'user_id': self.env.user.id,
                'activity_category': 'default',
                'res_model': 'order.track',
                'res_model_id': res_model_id.id,
                'res_id': self.id,
                'dd': plan_date,
                'order_track_id': self.id,
                'reminder_ids': [(6, 0, alarm_dic)],
            })
            self.plan_date_customer_finish = plan_date
            self.write({
                'plan_date_customer_finish_activity': plan_check_line_activity.id,
            })
        else:
            print('plan_date_akiny', plan_date)
            self.plan_date_customer_finish_activity.write({
                'dd': plan_date,
                'reminder_ids': [(6, 0, alarm_dic)],
            })
            self.plan_date_customer_finish = plan_date

    def open_activity_id_date_out_in(self):
        return {
            'name': u'登记完成时间',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.plan_date_out_in_activity.id,
            'target': 'new',
            'context': {'finish': 1}
        }

    def open_activity_id_date_ship(self):
        return {
            'name': u'登记完成时间',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.plan_date_ship_activity.id,
            'target': 'new',
            'context': {'finish': 1}
        }

    def open_activity_id_customer_finish(self):
        return {
            'name': u'登记完成时间',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.plan_date_customer_finish_activity.id,
            'target': 'new',
            'context': {'finish': 1}
        }




    def open_wizard_comments(self):
        wzcomments_obj = self.env['wizard.plan.check.comments']
        wzcomments = wzcomments_obj.create({
            'order_track_id':self.id,
            'type':self.type,
        })

        form_view = self.env.ref('yjzy_extend.wizard_plan_check_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.plan.check.comments',
            'type': 'ir.actions.act_window',
            'views': [ (form_view.id, 'form')],
            'res_id': wzcomments.id,
            'target': 'new',
        }


    def compute_planning_integrity(self):
        for one in self:
            if len(one.plan_check_line_ids) == len(
                    one.plan_check_line_ids.filtered(lambda x: x.state == '10_un_planning')):
                planning_integrity = '10_un_planning'
            elif len(one.plan_check_line_ids.filtered(lambda x: x.state == '10_un_planning')) == 0:
                planning_integrity = '30_planning'
            else:
                planning_integrity = '20_part_un_planning'
            print('akiny_planning_3',planning_integrity)
            one.write({
                'planning_integrity':planning_integrity
            })

    def open_planning_integrity(self):
        tree_view = self.env.ref('yjzy_extend.plan_check_line_tree_view')
        form_view = self.env.ref('yjzy_extend.plan_check_line_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'plan.check.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'),(form_view.id, 'form')],
            'domain':[('order_track_id', '=', self.id)],
            # 'res_id': self.id,
            'context':{'group_by':'state'},
            'target': 'current',
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }
    def open_check_on_time(self):
        tree_view = self.env.ref('yjzy_extend.plan_check_line_tree_view')
        form_view = self.env.ref('yjzy_extend.plan_check_line_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'plan.check.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'),(form_view.id, 'form')],
            'domain':[('order_track_id', '=', self.id)],
            # 'res_id': self.id,
            'target': 'current',
            'context':{'group_by':'state'}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def compute_check_on_time(self):
        for one in self:
            print('akiny_planning',len(one.plan_check_line_ids.filtered(lambda x: x.state == '30_time_out_planning')))
            if len(one.plan_check_line_ids) == len(
                    one.plan_check_line_ids.filtered(lambda x: x.state in ['20_planning'])):
                check_on_time = '10_not_time'
            elif len(one.plan_check_line_ids) == len(
                    one.plan_check_line_ids.filtered(lambda x: x.state in ['10_un_planning'])):
                check_on_time = '10_not_time'
            elif len(one.plan_check_line_ids.filtered(lambda x: x.state == '30_time_out_planning')) > 0:
                check_on_time = '20_out_time_un_finish'
            elif len(one.plan_check_line_ids.filtered(lambda x: x.state == '50_time_out_finish')) > 0:
                check_on_time = '40_out_time_finish'
            elif len(one.plan_check_line_ids.filtered(lambda x: x.state in ['50_time_out_finish','40_finish'])) == 0:
                check_on_time = '10_not_time'
            else:
                check_on_time = '30_on_time_finish'
            one.write({
                'check_on_time': check_on_time
            })


    def open_so_id(self):
        form_view = self.env.ref('yjzy_extend.new_sale_order_form_4')
        return {
            'name': u'销售合同',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'sale.order',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.so_id.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_tb_id(self):
        form_view = self.env.ref('yjzy_extend.view_transport_bill_tenyale_sales_form')
        return {
            'name': u'出运合同',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'transport.bill',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.tb_id.id,
            'target': 'current',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_factory_return(self):
        form_view = self.env.ref('yjzy_extend.order_track_form')
        return {
            'name': u'工厂回签日期',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'order.track',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'new',
            'context': {'return': 1,
                        'open':1}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    def open_order_track(self):
        form_view = self.env.ref('yjzy_extend.order_track_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'order.track',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'context':{'order_track':1,'type':'new_order_track'}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }
    def open_order_track_tb(self):
        form_view = self.env.ref('yjzy_extend.order_track_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'order.track',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'context':{'type':'transport_track'}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }
    #这个打开的还是plan.check
    def open_plan_check_line(self):
        form_view = self.env.ref('yjzy_extend.order_track_form_plan_check_ids')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'order.track',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'context':{}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }
    #这个才是真的打开plan.check.line
    def open_plan_check_line_new(self):
        tree_view = self.env.ref('yjzy_extend.plan_check_line_tree_view')
        form_view = self.env.ref('yjzy_extend.plan_check_line_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'plan.check.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'),(form_view.id, 'form')],
            'domain':[('order_track_id', '=', self.id)],
            # 'res_id': self.id,
            'target': 'current',
            'context':{'group_by':'po_id'}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    def compute_category_ids(self):
        for one in self:
            cat_dic = []
            category_obj = self.env['order.track.category']
            un_planning = category_obj.search([('name','=','未计划')])
            part_planning = category_obj.search([('name','=','部分计划')])
            part_time_out = category_obj.search([('name','=','部分过期')])
            all_time_out = category_obj.search([('name','=','全部过期')])
            if one.plan_check_line_ids:
                if len(one.plan_check_line_ids) == len(
                        one.plan_check_line_ids.filtered(lambda x: x.state == '10_un_planning')):
                    cat_dic.append(un_planning.id)
                elif len(one.plan_check_line_ids) == len(one.plan_check_line_ids.filtered(lambda x: x.state == '30_time_out_planning')):
                    cat_dic.append(all_time_out.id)
                else:
                    if len(one.plan_check_line_ids.filtered(lambda x: x.state == '30_time_out_planning')) > 0 :
                        cat_dic.append(part_time_out.id)
                    if len(one.plan_check_line_ids.filtered(lambda x: x.state == '10_un_planning')) > 0:
                        cat_dic.append(part_planning.id)
                print('cat_dic_akiny',cat_dic)
                one.write({'category_ids':[(6, 0, cat_dic)]})


    def action_date_out_in(self):
        if self.date_out_in and not self.is_date_out_in:
            plan_check_obj = self.env['plan.check']
            self.tb_id.with_context({'date_type':'date_out_in'}).action_customer_date_state_done()
            self.tb_id.sale_invoice_id.write({
                'order_track_id':self.id,
            })
            for line in self.tb_id.purchase_invoice_ids:
                line.write({
                    'order_track_id': self.id
                })
            for one in self.tb_id.purchase_invoice_ids:
                plan_check = plan_check_obj.create({
                    'type': 'transport_track',
                    'tb_id': self.tb_id.id,
                    'purchase_invoice_id': one.id,
                    'order_track_id': self.id,
                })
            self.is_date_out_in = True

    #预计的船期填写日期




    def open_purchase_invoice(self):
        form_view = self.env.ref('yjzy_extend.view_account_supplier_invoice_new_form')
        tree_view = self.env.ref('yjzy_extend.view_account_invoice_new_tree_track')
        self.ensure_one()
        return {
            'name': u'供应商日期填制',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'), (form_view.id, 'form')],
            'domain': [('id', 'in', [x.id for x in self.tb_purchase_invoice_ids])],
            'target':'new'
        }



class PlanCheck(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _name = 'plan.check'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = '计划跟踪明细'

    @api.depends('plan_check_line', 'plan_check_line.date_finish')
    def compute_date_finish(self):
        for one in self:
            date_finish = False
            for x in one.plan_check_line:
                if not date_finish:
                    if x.date_finish:
                        date_finish = x.date_finish
                    else:
                        date_finish = False
                else:
                    if x.date_finish:
                        if date_finish < x.date_finish:
                            date_finish = x.date_finish
                        else:
                            date_finish = date_finish
            one.date_finish = date_finish

    @api.depends('plan_check_line','plan_check_line.date_deadline')
    def compute_date_deadline(self):
        for one in self:
            date_deadline = False
            for x in one.plan_check_line:
                if not date_deadline:
                    if x.date_deadline:
                        date_deadline = x.date_deadline
                    else:
                        date_deadline = False
                else:
                    if x.date_deadline:
                        if date_deadline < x.date_deadline:
                            date_deadline = x.date_deadline
                        else:
                            date_deadline = date_deadline
            print('date_deadline_akiny',date_deadline)
            one.date_deadline = date_deadline

    @api.depends('po_id','po_id.date_planned','po_id.date_order')
    def compute_date_po_planned_order(self):
        for one in self:
            one.date_po_planned = one.po_id.date_planned
            one.date_po_order = one.po_id.date_order


    def compute_display_name(self):
        ctx = self.env.context
        for one in self:
            if ctx.get('factory_return'):
                if one.date_factory_return:
                    if one.po_id.contract_code:
                        display_name = '%s:%s' %( one.po_id.contract_code,one.date_factory_return)
                    else:
                        display_name = '%s:%s' % ('无合同号', one.date_factory_return)
                else:
                    display_name = '%s:%s' % (one.po_id.contract_code, '未回签')
            else:
                if one.po_id.contract_code:
                    display_name = one.po_id.contract_code
                else:
                    display_name = '%s' % ('无合同号')
            one.display_name = display_name

    @api.depends('plan_check_line','plan_check_line.state')
    def compute_state(self):
        for one in self:
            if len(one.plan_check_line.filtered(lambda x: x.state != 'planning')) == len(one.plan_check_line):
                one.state = 'finish'
            else:
                one.state = 'planning'

    @api.depends('so_id', 'tb_id', 'so_id.company_id', 'tb_id.company_id')
    def compute_company_id(self):
        for one in self:
            if one.order_track_id.type in ['new_order_track', 'order_track']:
                company_id = one.so_id.company_id
            else:
                company_id = one.tb_id.company_id
            one.company_id = company_id


    def compute_plan_check_att_count(self):
        for one in self:
            one.plan_check_att_count = len(one.plan_check_att)

    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track', '出运单跟踪')],
                            'type', related='order_track_id.type')
    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    order_track_id = fields.Many2one('order.track','计划跟踪',ondelete='cascade')
    # plan_check_ids = fields.One2many('plan.check','so_id')
    so_id = fields.Many2one('sale.order',ondelete='cascade')

    po_id = fields.Many2one('purchase.order','采购合同',ondelete='cascade')

    date_factory_return = fields.Date('工厂回传时间', index=True,track_visibility='onchange', related='po_id.date_factory_return',store=True)#todo 填写后，自动写入po
    date_po_planned = fields.Date('工厂交期',compute=compute_date_po_planned_order,store=True)
    date_po_order = fields.Date('工厂下单日期',compute=compute_date_po_planned_order,store=True)
    plan_check_line = fields.One2many('plan.check.line', 'plan_check_id')
    is_on_time = fields.Boolean('是否准时完成')
    date_finish = fields.Date('完成时间',compute=compute_date_finish)
    date_deadline = fields.Date('计划时间', compute=compute_date_deadline)

    state = fields.Selection([('planning','执行中'),('finish','完成'),],'状态', default='planning',compute=compute_state,store=True)

    tb_id = fields.Many2one('transport.bill','出运合同')
    purchase_invoice_id = fields.Many2one('account.invoice','采购账单')
    supplier_delivery_date = fields.Date('工厂实际发货日期')
    purchase_invoice_date_finish = fields.Date('供应商交单时间', related='purchase_invoice_id.date_finish', store=True)

    company_id = fields.Many2one('res.company', '公司', compute=compute_company_id,store=True)

    planning_integrity = fields.Selection(
        [('10_un_planning', '未计划'), ('20_part_un_planning', '部分未计划'), ('30_planning', '已完全计划')],
        u'计划安排完整性', default='10_un_planning')
    check_on_time = fields.Selection(
        [('10_not_time', u'未到时'), ('20_out_time_un_finish', u'超时未完成'), ('30_on_time_finish', u'准时完成'),
         ('40_out_time_finish', u'超时完成')],
        u'检查执行准时性', default='10_not_time')
    comments = fields.Text('备注日志', track_visibility='onchange')

    plan_check_att = fields.One2many('order.track.attachment', 'plan_check_id',
                                          string='采购交单附件')
    plan_check_att_count = fields.Integer('附件数量', compute=compute_plan_check_att_count)

    def open_self(self):
        form_view = self.env.ref('yjzy_extend.view_plan_check').id
        return {
            'name': '检查点附件',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plan.check',
            'type': 'ir.actions.act_window',
            'views': [(form_view, 'form')],
            'res_id': self.id,
            'target': 'new'
        }



    def compute_planning_integrity(self):
        for one in self:
            if len(one.plan_check_line) == len(
                    one.plan_check_line.filtered(lambda x: x.state == '10_un_planning')):
                planning_integrity = '10_un_planning'
            elif len(one.plan_check_line.filtered(lambda x: x.state == '10_un_planning')) == 0:
                planning_integrity = '30_planning'
            else:
                planning_integrity = '20_part_un_planning'
            print('akiny_planning_3',planning_integrity)
            one.write({
                'planning_integrity':planning_integrity
            })

    def compute_check_on_time(self):
        for one in self:
            print('akiny_planning',len(one.plan_check_line.filtered(lambda x: x.state == '30_time_out_planning')))
            if len(one.plan_check_line) == len(
                    one.plan_check_line.filtered(lambda x: x.state in ['20_planning'])):
                check_on_time = '10_not_time'
            elif len(one.plan_check_line) == len(
                    one.plan_check_line.filtered(lambda x: x.state in ['10_un_planning'])):
                check_on_time = '10_not_time'
            elif len(one.plan_check_line.filtered(lambda x: x.state == '30_time_out_planning')) > 0:
                check_on_time = '20_out_time_un_finish'
            elif len(one.plan_check_line.filtered(lambda x: x.state == '50_time_out_finish')) > 0:
                check_on_time = '40_out_time_finish'
            elif len(one.plan_check_line.filtered(lambda x: x.state in ['50_time_out_finish','40_finish'])) == 0:
                check_on_time = '10_not_time'
            else:
                check_on_time = '30_on_time_finish'
            one.write({
                'check_on_time': check_on_time
            })

    # def name_get(self):
    #     res = []
    #     for order in self:
    #         name = '%s' % (order.display_name)
    #         res.append(name)
    #     return res


    #
    # def open_plan_check_line(self):
    #     return {
    #         'name': u'检查点',
    #         'view_type': 'form',
    #         'view_mode': 'form',
    #         'res_model': 'plan.check',
    #         'type': 'ir.actions.act_window',
    #         'res_id': self.id,
    #         'target': 'current',
    #         'context': {
    #         }
    #     }
    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    def open_plan_check_ids(self):
        form_view = self.env.ref('yjzy_extend.plan_check_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plan.check',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.id,
            'target': 'current',
            'context': {}
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }


    def open_planning_integrity(self):
        tree_view = self.env.ref('yjzy_extend.plan_check_line_tree_view')
        form_view = self.env.ref('yjzy_extend.plan_check_line_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'tree',
            'res_model': 'plan.check.line',
            'type': 'ir.actions.act_window',
            'views': [(tree_view.id, 'tree'),(form_view.id, 'form')],
            'domain':[('plan_check_id', '=', self.id)],
            # 'res_id': self.id,
            'context':{'group_by':'state'},
            'target': 'current',
            # 'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}}
        }


    def open_wizard_comments(self):
        wzcomments_obj = self.env['wizard.plan.check.comments']
        wzcomments = wzcomments_obj.create({
            'plan_check_id': self.id,
        })

        form_view = self.env.ref('yjzy_extend.wizard_plan_check_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.plan.check.comments',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': wzcomments.id,
            'target': 'new',
            'context':{'check_type':'plan_check'}
        }

class PlanCheckLine(models.Model):
    """ An actual activity to perform. Activities are linked to
    documents using res_id and res_model_id fields. Activities have a deadline
    that can be used in kanban view to display a status. Once done activities
    are unlinked and a message is posted. This message has a new activity_type_id
    field that indicates the activity linked to the message. """
    _name = 'plan.check.line'
    _inherit = ['mail.thread', 'mail.activity.mixin', 'portal.mixin']
    _description = '检查点明细'

    # 计算state
    @api.depends('date_finish', 'date_deadline')
    def compute_state(self):
        strptime = datetime.strptime
        now = datetime.now()
        for one in self:
            if not one.date_deadline:
                state = '10_un_planning'
            else:
                if one.date_finish:
                    times_finish = (strptime(one.date_finish, DF) - strptime(one.date_deadline, DF)).days
                    if times_finish <= 0:
                        state = '40_finish'
                        one.is_on_time = True
                    else:
                        state = '50_time_out_finish'
                else:
                    time_out = (now - fields.Datetime.from_string(one.date_deadline)).days
                    print('time_out_akiny',time_out)
                    if  time_out > 0:
                        state = '30_time_out_planning'
                    else:
                        state = '20_planning'
            one.state = state
            one.order_track_id.compute_category_ids()
            one.order_track_id.compute_planning_integrity()
            one.order_track_id.compute_check_on_time()
            one.order_track_id.compute_check_number_percent()
            one.plan_check_id.compute_planning_integrity()
            one.plan_check_id.compute_check_on_time()


    def compute_display_name(self):
        ctx = self.env.context
        for one in self:
            one.display_name = one.activity_type_1_id.name

    def compute_remaining_time(self):
        strptime = datetime.strptime
        for one in self:
            if one.date_deadline:
                remaining_time = strptime(one.date_deadline, DF) - datetime.today()
                one.remaining_time = remaining_time.days
            else:
                one.remaining_time = -999
    def compute_plan_check_line_att_count(self):
        for one in self:
            one.plan_check_line_att_count = len(one.plan_check_line_att)


    display_name = fields.Char(u'显示名称', compute=compute_display_name)

    order_track_id = fields.Many2one('order.track','计划跟踪',ondelete='cascade')
    plan_check_id = fields.Many2one('plan.check','计划检查',ondelete='cascade' )
    po_id = fields.Many2one('purchase.order',related='plan_check_id.po_id',store=True)
    company_id = fields.Many2one('res.company', '公司', related='po_id.company_id')
    date_finish = fields.Date('检查点完成时间',)
    date_deadline = fields.Date('检查点计划时间', index=True, required=False, )

    state = fields.Selection([('10_un_planning','未计划'),('20_planning','计划中'),('30_time_out_planning','已过期'),('40_finish','正常完成'),('50_time_out_finish','超时完成')],'状态', default='10_un_planning',
                             compute=compute_state,store=True)
    is_on_time = fields.Boolean('是否准时完成')
    activity_id = fields.Many2one('mail.activity','计划活动')

    activity_type_1_id = fields.Many2one('mail.activity.type','检查类型' )
    comments_line = fields.Text('工厂检查明细备注',track_visibility='onchange')

    remaining_time = fields.Integer('剩余时间', compute=compute_remaining_time,)
    attachment = fields.Many2many('ir.attachment', string='附件')
    plan_check_line_att = fields.One2many('order.track.attachment', 'plan_check_line_id',
                                               string='检查点附件')
    plan_check_line_att_count = fields.Integer('附件数量', compute=compute_plan_check_line_att_count)

    def open_self(self):
        form_view = self.env.ref('yjzy_extend.view_plan_check_line').id
        return {
            'name': '检查点附件',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'plan.check.line',
            'type': 'ir.actions.act_window',
            'views': [(form_view, 'form')],
            'res_id': self.id,
            'target': 'new'
        }


    def open_activity_id(self):
        return {
            'name': u'活动',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.activity_id.id,
            'target': 'new',
            'context': {}
        }

    def open_activity_id_plan(self):
        return {
            'name': u'登记计划时间',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.activity_id.id,
            'target': 'new',
            'context': {'plan':1}
        }

    def open_activity_id_finish(self):
        return {
            'name': u'登记完成时间',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'mail.activity',
            'type': 'ir.actions.act_window',
            'res_id': self.activity_id.id,
            'target': 'new',
            'context': {'finish': 1}
        }

    def open_wizard_comments(self):
        wzcomments_obj = self.env['wizard.plan.check.comments']
        wzcomments = wzcomments_obj.create({
            'plan_check_line_id': self.id,

        })

        form_view = self.env.ref('yjzy_extend.wizard_plan_check_form')
        return {
            'name': u'查看',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.plan.check.comments',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': wzcomments.id,
            'target': 'new',
        }




