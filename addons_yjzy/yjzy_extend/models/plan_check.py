# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import api, exceptions, fields, models, _
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT as DATETIME_FORMAT
from datetime import datetime, timedelta,date


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
            strptime = datetime.strptime
            today = datetime.today()
            time_contract_requested = one.time_contract_requested
            x = (today - strptime(one.date_so_contract , DF)).days
            print('x_akiny',x,time_contract_requested)
            finish_percent = time_contract_requested != 0 and x * 100 / time_contract_requested or 0
            if finish_percent >= 100:
                finish_percent = 100
            one.finish_percent = finish_percent

    def compute_finish_percent_supplier(self):
        for one in self:
            strptime = datetime.strptime
            today = datetime.today()
            time_supplier_requested = one.time_supplier_requested
            x = (today - strptime(one.earliest_date_po_order, DF)).days
            finish_percent_supplier = time_supplier_requested != 0 and x * 100 / time_supplier_requested or 0
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
    def compute_check_finish_number(self):
        for one in self:
            num = 0
            for line in one.plan_check_ids:
                if line.plan_check_line:
                    for x in line.plan_check_line:
                        if x.state in ['ahead_of_time', 'on_time', 'time_out']:
                            num += 1
            one.check_finish_number = num

    def compute_check_number_percent(self):
        for one in self:
            check_number_percent = one.check_all_number !=0 and  one.check_finish_number * 100 / one.check_all_number or 0
            one.check_number_percent = check_number_percent

    def compute_display_name(self):
        ctx = self.env.context
        for one in self:
            display_name = '%s' % ('采购合同检查登记总表')
            one.display_name = display_name






    category_ids = fields.Many2many(
        'order.track.category','order_track_category_rel',  'track_id','category_id',
        string='Tags',store=True)
    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    type = fields.Selection([('new_order_track', '新订单下单前跟踪'), ('order_track', '订单跟踪'), ('transport_track','出运单跟踪')], 'type')
    so_id = fields.Many2one('sale.order', '销售合同' ,ondelete='cascade')
    tb_id = fields.Many2one('transport.bill', '出运合同' ,ondelete='cascade')
    po_ids = fields.Many2many('purchase.order','ref_pp', 'fid', 'tid','采购单')
    company_id = fields.Many2one('res.company', '公司', related='so_id.company_id')

    time_draft_order = fields.Datetime('so_create_date',related='so_id.create_date',store=True)
    hegui_date = fields.Date('合规审批时间',track_visibility='onchange',related='so_id.hegui_date',store=True)
    time_receive_pi = fields.Date('收到客户订单时间',track_visibility='onchange',related='so_id.time_receive_pi',store=True)
    time_sent_pi = fields.Date('发送PI时间',track_visibility='onchange',related='so_id.time_sent_pi',store=True)
    time_sign_pi = fields.Date('客户PI回签时间',track_visibility='onchange',related='so_id.time_sign_pi',store=True)

    date_so_contract = fields.Date('客户下单日期',related='so_id.contract_date',store=True)
    date_so_requested = fields.Datetime('客户交期',related='so_id.requested_date',store=True)

    time_contract_requested = fields.Integer('客户交期时限',compute=compute_time_contract_requested,store=True)
    finish_percent = fields.Float('完成期限比例',compute=compute_finish_percent)


    earliest_date_po_order = fields.Date('最早供应商下单时间',compute=compute_earliest_date_po_order,store=True)
    latest_date_po_planned = fields.Date('最迟供应商交单时间',compute=compute_latest_date_po_planned,stire=True)

    time_supplier_requested = fields.Integer('供应商交期时限', compute=compute_time_supplier_requested, store=True)
    finish_percent_supplier = fields.Float('供应商完成期限比例', compute=compute_finish_percent_supplier)
    #供应商总的分步检查数量
    check_all_number = fields.Integer('供应商总分步检查数',compute=compute_check_all_number,store=True)
    check_finish_number = fields.Integer('供应商完成分步检查数',compute=compute_check_finish_number, store =True)
    check_number_percent = fields.Float('分步完成比例',compute=compute_check_number_percent)

    plan_check_ids = fields.One2many('plan.check','order_track_id','计划跟踪明细')
    factory_return = fields.One2many('plan.check','order_track_id','工厂回签日期',)
    plan_check_line_ids = fields.One2many('plan.check.line','order_track_id','计划跟踪详情')

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
            'context':{'order_track':1}
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
            part_planning = category_obj.search([('name','=','部分未计划')])
            part_time_out = category_obj.search([('name','=','部分过期')])
            all_time_out = category_obj.search([('name','=','全部过期')])
            if one.plan_check_line_ids:
                if len(one.plan_check_line_ids) == len(
                        one.plan_check_line_ids.filtered(lambda x: x.state == 'un_planning')):
                    cat_dic.append(un_planning.id)
                elif len(one.plan_check_line_ids) == len(one.plan_check_line_ids.filtered(lambda x: x.state == 'time_out_planning')):
                    cat_dic.append(all_time_out.id)
                else:
                    if len(one.plan_check_line_ids.filtered(lambda x: x.state == 'time_out_planning')) > 0 :
                        cat_dic.append(part_time_out.id)
                    if len(one.plan_check_line_ids.filtered(lambda x: x.state == 'un_planning')) > 0:
                        cat_dic.append(part_planning.id)
                print('cat_dic_akiny',cat_dic)
                one.write({'category_ids':[(6, 0, cat_dic)]})


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



    display_name = fields.Char(u'显示名称', compute=compute_display_name)
    order_track_id = fields.Many2one('order.track','计划跟踪',ondelete='cascade')
    # plan_check_ids = fields.One2many('plan.check','so_id')
    so_id = fields.Many2one('sale.order',)
    company_id = fields.Many2one('res.company', '公司', related='so_id.company_id')
    po_id = fields.Many2one('purchase.order','采购合同')
    tb_id = fields.Many2one('transport.bill',related='order_track_id.tb_id')
    date_factory_return = fields.Date('工厂回传时间', index=True,track_visibility='onchange', related='po_id.date_factory_return',store=True)#todo 填写后，自动写入po
    date_po_planned = fields.Date('工厂交期',compute=compute_date_po_planned_order,store=True)
    date_po_order = fields.Date('工厂下单日期',compute=compute_date_po_planned_order,store=True)
    plan_check_line = fields.One2many('plan.check.line', 'plan_check_id')
    is_on_time = fields.Boolean('是否准时完成')
    date_finish = fields.Date('完成时间',compute=compute_date_finish)
    date_deadline = fields.Date('计划时间', compute=compute_date_deadline)

    state = fields.Selection([('planning','执行中'),('finish','完成'),],'状态', default='planning',compute=compute_state,store=True)


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
                state = 'un_planning'
            else:
                if one.date_finish:
                    times_finish = (strptime(one.date_finish, DF) - strptime(one.date_deadline, DF)).days
                    if times_finish <= 0:
                        state = 'finish'
                        one.is_on_time = True
                    else:
                        state = 'time_out_finish'
                else:
                    time_out = (now - fields.Datetime.from_string(one.date_deadline)).days
                    print('time_out_akiny',time_out)
                    if  time_out > 0:
                        state = 'time_out_planning'
                    else:
                        state = 'planning'
            one.state = state
            one.order_track_id.compute_category_ids()

    order_track_id = fields.Many2one('order.track','计划跟踪',ondelete='cascade')
    plan_check_id = fields.Many2one('plan.check','计划检查',ondelete='cascade' )
    po_id = fields.Many2one('purchase.order',related='plan_check_id.po_id',store=True)
    company_id = fields.Many2one('res.company', '公司', related='po_id.company_id')
    date_finish = fields.Date('检查点完成时间',)
    date_deadline = fields.Date('检查点计划时间', index=True, required=False, )


    state = fields.Selection([('un_planning','未计划'),('planning','计划中'),('time_out_planning','已过期'),('finish','正常完成'),('time_out_finish','超时完成')],'状态', default='un_planning',
                             compute=compute_state,store=True)
    is_on_time = fields.Boolean('是否准时完成')
    activity_id = fields.Many2one('mail.activity','计划活动')

    activity_type_1_id = fields.Many2one('mail.activity.type','检查类型' )

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







