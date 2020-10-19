# -*- coding: utf-8 -*-

from odoo import models, fields, api,_
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, float_compare

from odoo.addons import decimal_precision as dp


Hr_Expense_Selection = [('draft',u'草稿'),
                         ('employee_approval',u'待责任人确认'),
                         ('account_approval',u'待财务审批'),
                         ('manager_approval',u'待总经理审批'),
                         ('post',u'审批完成待支付'),
                         ('done',u'完成'),
                         ('refused', u'已拒绝'),
                         ('cancel', u'取消'),
                        ]

class ExpenseSheetStage(models.Model):

    _name = "expense.sheet.stage"
    _description = "Expense Stage"
    _order = 'sequence'

    name = fields.Char('Stage Name', translate=True, required=True)
    code = fields.Char('code')
    sequence = fields.Integer(help="Used to order the note stages", default=1)
    state = fields.Selection(Hr_Expense_Selection, 'State', default=Hr_Expense_Selection[0][0]) #track_visibility='onchange',
    fold = fields.Boolean('Folded by Default')
    # _sql_constraints = [
    #     ('name_code', 'unique(code)', u"编码不能重复"),
    # ]
    user_ids = fields.Many2many('res.users', 'ref_expense_users', 'fid', 'tid', 'Users') #可以进行判断也可以结合自定义视图模块使用
    group_ids = fields.Many2many('res.groups', 'ref_expense_group', 'gid', 'bid', 'Groups')

class hr_expense_sheet(models.Model):
    _inherit = 'hr.expense.sheet'

    def _default_bank_journal(self):
        # bank_journal_id   当是费用报告的时候 他默认 yfdrl  当是其他收入的时候 ysdrl
        ctx = self.env.context
        default_bank_journal_code = ctx.get('default_bank_journal_code', 'yfdrl')
        if default_bank_journal_code:
            journal = self.env['account.journal'].search([('code', '=', default_bank_journal_code), ('company_id', '=', self.env.user.company_id.id)], limit=1)
            if not journal:
                raise Warning('没有找到 默认银行日记账%s' % default_bank_journal_code)
            return journal.id

        return None

    def _default_partner(self):
        partner = self.env['res.partner'].search([('name', '=', u'未定义的')], limit=1)
        return partner

    @api.depends('total_amount','expense_line_ids', 'expense_line_ids.total_amount', 'expense_line_ids.currency_id')
    def _compute_negative_total_amount(self):
        for one in self:
            one.negative_total_amount = -1 * one.total_amount

    def _default_back_tax_product(self):
        try:
            return self.env.ref('yjzy_extend.product_back_tax').id
        except Exception as e:
            return None


    @api.depends('currency_id', 'total_amount', 'company_currency_id')
    def compute_total_amount_currency(self):
        # self.ensure_one() 只需要计算一条记录
        for one in self:
            total_currency_amount = one.currency_id.compute(one.total_amount, one.company_currency_id)
            one.company_currency_total_amount = total_currency_amount
    def _default_other_payment_invoice_product_id(self):
        try:
            return self.env.ref('yjzy_extend.product_back_tax').id
        except Exception as e:
            return None

    @api.model
    def _default_expense_sheet_stage(self):
        stage = self.env['expense.sheet.stage']
        return stage.search([], limit=1)

    def compute_tb_po_invoice_ids_count(self):
        for one in self:
            one.tb_po_invoice_ids_count = len(one.tb_po_invoice_ids)

    stage_id = fields.Many2one(
        'expense.sheet.stage',
        default=_default_expense_sheet_stage)

    #024 自动生成应收发票
    other_payment_invoice_product_id = fields.Many2one('product.product', u'其他应收项目', domain=[('type', '=', 'service')],
                                          default=_default_other_payment_invoice_product_id)
    other_payment_invoice_amount = fields.Monetary(u'其他应收金额')
    other_payment_invoice_id = fields.Many2one('account.invoice', u'其他应收发票')
    #0911
    expense_type_new = fields.Selection([('exp_to_pay',u'先申请后付款'),('pay_to_exp',u'先付款后申请')],u'费用生成类型')
    expense_to_invoice_type = fields.Selection([('normal',u'常规费用'),('to_invoice',u'转为货款'),('other_payment',u'其他支出'),('incoming',u'其他收入')],u'类型说明')
    #901
    tb_po_invoice_ids = fields.One2many('tb.po.invoice','expense_sheet_id',u'费用转采购申请单')
    tb_po_invoice_ids_count = fields.Integer('费用转采购申请单', compute=compute_tb_po_invoice_ids_count)

    #819费用创建应付发票
    invoice_id = fields.Many2one('account.invoice',u'Invoice')
    is_to_invoice = fields.Boolean(u'是否转货款')

    todo_cron = fields.Boolean(u'可以执行')
    include_tax = fields.Boolean(u'含税')

    yjzy_payment_id = fields.Many2one('yjzy.account.payment', u'新付款单')

    payment_id = fields.Many2one('account.payment', u'付款单ID')
    yjzy_payment_currency_id = fields.Many2one('res.currency', u'付款单ID币种', related='payment_id.currency_id')
    balance = fields.Monetary(related='payment_id.balance', currency_field='yjzy_payment_currency_id')

    employee_user_id = fields.Many2one('res.users', related='employee_id.user_id', string='职员用户', readonly=True)

    partner_id = fields.Many2one('res.partner', u'Partner', default=lambda self: self._default_partner(), )
    fk_journal_id = fields.Many2one('account.journal', u'日记账')
    is_split = fields.Boolean(u'是否分别付款')

    bank_id = fields.Many2one('res.partner.bank', u'银行账号')
    bank_journal_id = fields.Many2one('account.journal', string='Bank Journal', states={'done': [('readonly', True)], 'post': [('readonly', True)]},
                                      default=lambda self: self._default_bank_journal(),
                                      help="The payment method used when the expense is paid by the company.")
    negative_total_amount = fields.Monetary(u'负数总计', currency_field='currency_id', store=True, compute=_compute_negative_total_amount)
    back_tax_product_id = fields.Many2one('product.product', u'退税产品', domain=[('type', '=', 'service')], default=_default_back_tax_product)
    back_tax_amount = fields.Monetary(u'退税金额')
    back_tax_invoice_id = fields.Many2one('account.invoice', u'退税发票')

    all_line_is_confirmed = fields.Boolean('责任人已全部确认', compute='compute_all_line_is_confirmed')

    document_number = fields.Integer(u'单据数量')
    account_confirm_uid = fields.Many2one('res.users', u'财务审批')

    manager_confirm_uid = fields.Many2one('res.users', u'总经理审批')

    my_total_amount = fields.Float(string='权限金额', compute='compute_my_total_amount', digits=dp.get_precision('Account'))
    my_expense_line_ids = fields.One2many('hr.expense', compute='compute_my_total_amount', string='权限明细')
    my_expense_line_ids_b = fields.One2many('hr.expense', compute='compute_my_total_amount', string='权限明细')
    my_expense_line_ids_employee = fields.One2many('hr.expense', compute='compute_my_total_amount', string='权限明细')
    my_expense_line_ids_company = fields.One2many('hr.expense', compute='compute_my_total_amount', string='权限明细')

    total_this_moth = fields.Float(u'本月费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    total_this_year = fields.Float(u'今年费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    #akiny
    total_approve = fields.Float(u'已完成审批未支付费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    total_submit = fields.Float(u'已提交未完成审批费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    total_un_submit = fields.Float(u'未提交的费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))


    employee_wkf = fields.Boolean('责任人阶段')
    # akiny 审批确认信息记录
    employee_confirm_date = fields.Date('申请人确认日期')
    employee_confirm = fields.Many2one('res.users', u'申请人确认')

    account_confirm_date = fields.Date('财务审批日期')
    account_confirm = fields.Many2one('res.users', u'财务审批')

    manager_confirm = fields.Many2one('res.users', u'总经理审批')
    manager_confirm_date = fields.Date('总经理审批日期')
    state_1 = fields.Selection(Hr_Expense_Selection,u'审批流程',default='draft', index=True,related='stage_id.state',
                             track_visibility='onchange') #费用审批流程
    # state_2 = fields.Selection([('10_draft',u'草稿'),
    #                             ('20_submit',u'')])#收入审批流程
    state = fields.Selection(selection_add=[
                                            ('approval', u'审批中'),
                                            ('employee_approval', u'待责任人审批'),
                                            ('account_approval', u'待财务审批'),
                                            ('manager_approval', u'待总经理审批'),
                                            ('Approval', u'审批历史消息')])

    categ_id = fields.Many2one('product.category', '大类', )
    second_categ_id = fields.Many2one('product.category', '中类', )


    budget_type = fields.Selection("预算类型", related="categ_id.budget_type")


    expense_line_ids_b = fields.One2many('hr.expense', related='expense_line_ids')
    expense_line_ids_employee = fields.One2many('hr.expense', related='expense_line_ids')
    expense_line_ids_company = fields.One2many('hr.expense', related='expense_line_ids')
    gongsi_id = fields.Many2one('gongsi', '内部公司',default=lambda self: self.env.user.company_id.gongsi_id)

    #akiny
    is_budget = fields.Boolean(u'是否已预算')
    line_edit = fields.Boolean(u'明细是否可编辑')
    is_editable = fields.Boolean(u'可编辑')
    company_currency_id = fields.Many2one('res.currency', u'公司货币',
                                          default=lambda self: self.env.user.company_id.currency_id.id)
    company_currency_total_amount = fields.Monetary(u'本币合计', currency_field='company_currency_id', digits=(2, 4),compute=compute_total_amount_currency, store=True)






    #0926
    def _stage_find(self, domain=None, order='sequence'):
        search_domain = list(domain)
        return self.env['expense.sheet.stage'].search(search_domain, order=order, limit=1)

    def action_to_employee_approval(self):
        if self.expense_to_invoice_type == 'normal':
            if (self.employee_id.user_id == self.env.user or self.employee_id.name == '公司' or self.create_uid == self.env.user or self.env.user.id ==1 ) and self.total_amount >0:
                stage_id = self._stage_find(domain=[('code', '=', '020')])
                self.write({'stage_id': stage_id.id,
                            'employee_confirm': self.env.user.id,
                            'employee_confirm_date': fields.datetime.now(),
                            'employee_wkf': True,
                            'state': 'approval',
                                   })
                self.btn_user_confirm()
                self.btn_match_budget()
            else:
                raise Warning('非权限用户或者金额等于0，请检查！')
        elif self.expense_to_invoice_type == 'incoming':
            if self.total_amount < 0:
                stage_id = self._stage_find(domain=[('code', '=', '030')])
                self.write({'stage_id': stage_id.id,
                            'employee_confirm': self.env.user.id,
                            'employee_confirm_date': fields.datetime.now(),
                            'state': 'approval',
                            })
                self.btn_user_confirm()
            else:
                raise Warning('金额等于0，请检查！')
        elif self.expense_to_invoice_type == 'other_payment':
            if self.total_amount <=0:
                raise Warning('金额填写不正确，请检验！')
            if not  self.fk_journal_id:
                raise Warning('请填写付款账户！') 
            stage_id = self._stage_find(domain=[('code', '=', '040')])
            self.write({'stage_id': stage_id.id,
                        'employee_confirm': self.env.user.id,
                        'employee_confirm_date': fields.datetime.now(),
                        'state': 'approval',
                        })
            self.btn_user_confirm()


    def action_account_to_manager(self):
        if self.expense_to_invoice_type == 'normal' and self.employee_user_id == self.env.user:
            self.with_context(force=1).btn_user_confirm()
            self.action_account_approve()
        else:
            raise Warning('不允许直接提交总经理')


            #给管理员显示
    def action_to_account_approval(self):
        stage_id = self._stage_find(domain=[('code', '=', '030')])
        if self.expense_to_invoice_type == 'normal':
            if self.all_line_is_confirmed == False or self.total_amount == 0 or self.state_1 != 'employee_approval':
                raise Warning('费用明细没有完成审批或者总金额等于0，请查验！')
            else:
                stage_id = self._stage_find(domain=[('code', '=', '030')])
                self.write({'employee_wkf':False,
                            'stage_id': stage_id.id,
                            })
                self.btn_match_budget()
        elif self.expense_to_invoice_type == 'other_payment':
            if self.total_amount == 0:
                raise Warning('总金额不允许等于0，请查验！')
            else:
                self.write({'employee_wkf': False,
                            'stage_id': stage_id.id})

    # def action_to_account_approval_all(self):
    #     stage_id = self._stage_find(domain=[('code', '=', '030')])
    #     for one in self:
    #         if one.expense_to_invoice_type == 'normal':
    #             if one.all_line_is_confirmed == True and one.total_amount >= 0:
    #                 stage_id = one._stage_find(domain=[('code', '=', '030')])
    #                 one.write({'employee_wkf':False,
    #                             'stage_id': stage_id.id,
    #                             })
    #                 one.btn_match_budget()
    #         elif one.expense_to_invoice_type == 'other_payment':
    #             if one.total_amount >= 0:
    #                 one.write({'employee_wkf': False,
    #                             'stage_id': stage_id.id})


    #0925财务审批的时候判断是否已经转为货款
    def action_account_approve(self):
        if self.expense_to_invoice_type == 'to_invoice':
            stage_id = self._stage_find(domain=[('code', '=', '040')])
            if not self.fk_journal_id:
                raise Warning('请填写付款账号')
            if self.tb_po_invoice_ids:
                self.tb_po_invoice_ids.action_submit()
                self.write({'account_confirm': self.env.user.id,
                            'stage_id': stage_id.id,
                            'account_confirm_date':fields.datetime.now()})
            else:
                raise Warning('还没有生成费用转货款申请单，请检查！')
        elif self.expense_to_invoice_type == 'normal':
            stage_id = self._stage_find(domain=[('code', '=', '040')])
            if not self.fk_journal_id:
                raise Warning('请填写付款账号')
            else:
                self.write({'account_confirm': self.env.user.id,
                            'stage_id': stage_id.id,
                            'account_confirm_date': fields.datetime.now()})

        elif self.expense_to_invoice_type == 'incoming':
            stage_id = self._stage_find(domain=[('code', '=', '060')])
            if self.total_amount < 0:
                self.write({'account_confirm': self.env.user.id,
                            'stage_id': stage_id.id,
                            'account_confirm_date': fields.datetime.now()})
                self.approve_expense_sheets()
                self.action_sheet_move_create()
            else:
                raise Warning('金额出错，请检查！')

        # 819 总经理审批费用，也同时审批生成的费用转货款

    def action_manager_approve(self):
        stage_id = self._stage_find(domain=[('code', '=', '050')])
        if self.expense_to_invoice_type == 'to_invoice':
            if self.tb_po_invoice_ids:
                self.approve_expense_sheets()
                self.tb_po_invoice_ids.action_manager_approve()
                print('tb_po_invoice_ids',self.tb_po_invoice_ids)
                self.write({'manager_confirm': self.env.user.id,
                            'stage_id': stage_id.id,
                            'manager_confirm_date': fields.datetime.now()})
        elif self.expense_to_invoice_type == 'normal' or self.expense_to_invoice_type == 'other_payment':
            self.approve_expense_sheets()
            self.create_rcfkd()
            print('tb_po_invoice_ids', self.tb_po_invoice_ids)
            self.write({'manager_confirm': self.env.user.id,
                        'stage_id': stage_id.id,
                        'manager_confirm_date': fields.datetime.now()})

    def action_to_invoice_done(self):
        stage_id = self._stage_find(domain=[('code', '=', '060')])
        if self.expense_to_invoice_type == 'to_invoice':
            self.write({'stage_id': stage_id.id,
                        'state':'done',
                        })
            self.with_context(force=1).btn_user_confirm()#上面的状态改变后，会导致明细的状态被变化
        else:
            self.action_sheet_move_create()
            self.write({'stage_id': stage_id.id, })


    def action_refuse(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        stage_preview = self.stage_id
        user = self.env.user
        group = self.env.user.groups_id
        if self.state_1 in ['draft','employee_approval'] and self.employee_id.user_id != user:
            raise Warning('您不是申请人，无权拒绝!')
        if self.state_1 in ['done','post']:
            raise Warning('已完成不允许拒绝!')
        if self.state_1 not in ['draft','employee_approval','done','post'] and  user not in stage_preview.user_ids: #not stage_preview.user_ids and
            raise Warning('您没有权限拒绝!')
        self.write({'state': 'cancel',
                    'account_confirm': False,
                    'account_confirm_date': False,
                    'employee_confirm': False,
                    'employee_confirm_date': False,
                    'manager_confirm': False,
                    'manager_confirm_date': False,
                    'stage_id': stage_id.id,})
        self.btn_undo_confirm_force()
        self.btn_release_budget()
        if self.expense_to_invoice_type != 'incoming':
            self.payment_id.unlink()
            self.other_payment_invoice_id.unlink()
        if self.expense_to_invoice_type == 'to_invoice':
            self.tb_po_invoice_ids.unlink()
            self.expense_to_invoice_type = 'normal'
        for tb in self:
            tb.message_post_with_view('yjzy_extend.expense_sheet_template_refuse_reason',
                                      values={'reason': reason, 'name': self.name},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式

    def action_draft(self):
        stage_id = self._stage_find(domain=[('code', '=', '010')])
        # budget = self.env['budget.budget'].create({
        #     'type': 'transport',
        #     'tb_id': self.id,
        # })
        self.write({'state': 'draft',
                    'stage_id': stage_id.id})

    #责任人审批阶段的拒绝
    def action_refuse_user(self, reason):
        stage_id = self._stage_find(domain=[('code', '=', '090')])
        user = self.env.user
        group = self.env.user.groups_id
        if self.employee_id.user_id != user:
            raise Warning('您没有权限拒绝')
        else:
            self.write({'state': 'cancel',
                        'account_confirm': False,
                        'account_confirm_date': False,
                        'employee_confirm': False,
                        'employee_confirm_date': False,
                        'manager_confirm': False,
                        'manager_confirm_date': False,
                        'stage_id': stage_id.id, })
            self.btn_undo_confirm_force()
            self.btn_release_budget()
        for tb in self:
            tb.message_post_with_view('yjzy_extend.expense_sheet_template_refuse_reason',
                                      values={'reason': reason, 'name': self.ref},
                                      subtype_id=self.env.ref(
                                          'mail.mt_note').id)  # 定义了留言消息的模板，其他都可以参考，还可以继续参考费用发送计划以及邮件方式




    #payment_date_store = fields.Datetime(u'付款日期', related='payment_id.payment_date_confirm', store=True)
# #akiny
#     @api.depends('expense_line_ids', 'expense_line_ids.categ_id')
#     def _compute_categ(self):
#         categ_id = None
#
#         for expense in self.expense_line_ids:
#             categ_id = expense.categ_id
#         self.categ_id = categ_id
#
#     @api.depends('expense_line_ids', 'expense_line_ids.second_categ_id')
#     def _compute_second_categ(self):
#         second_categ_id = None
#         for expense in self.expense_line_ids:
#             second_categ_id = expense.second_categ_id
#         self.second_categ_id = second_categ_id
    #902更新历史的费用报告的总经理审批时间
    def compute_manager_approve_date_uid(self):
        # message_id = self.message_ids[0]
        message_id = self.message_ids.filtered(lambda x: x.create_uid.name == '奚海峰')
        message_id_1 = self.message_ids.filtered(lambda x: x.create_uid.name == 'administrator')
        if message_id:
            manager_confirm = message_id[0].create_uid
            manager_confirm_date =message_id[0].date
        else:
            manager_confirm = message_id_1[0].create_uid
            manager_confirm_date = message_id_1[0].date
        print('message_id', manager_confirm, manager_confirm_date)
        self.write({'manager_confirm': manager_confirm.id,
                    'manager_confirm_date': manager_confirm_date})



    def open_wizard_tb_po_invoice(self):
        self.ensure_one()
        bill_id = self.expense_line_ids.mapped('tb_id')
        wizard = self.env['wizard.tb.po.invoice'].create({'tb_id': bill_id and bill_id[0].id,
                                                          'expense_sheet_id':self.id,
                                                          'type':'expense_po'
                                                          })

        view = self.env.ref('yjzy_extend.wizard_tb_po_form')
        line_obj = self.env['wizard.tb.po.invoice.line']
        for hsl in bill_id.hsname_all_ids:
            line_obj.create({
                'wizard_id': wizard.id,
                'hs_id': hsl.hs_id.id,
                'hs_en_name': hsl.hs_en_name,
                'purchase_amount2_tax': hsl.purchase_amount2_tax,
                'purchase_amount2_no_tax': hsl.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast': hsl.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast': hsl.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest': hsl.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest': hsl.purchase_amount_min_add_rest,
                'hsname_all_line_id': hsl.id,
                'back_tax': hsl.back_tax
            })
        return {
            'name': _(u'创建采购单'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'wizard.tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': wizard.id,
            # 'context': { },
        }

    def open_wizard_tb_po_invoice_new(self):
        self.ensure_one()
        bill_id = self.expense_line_ids.mapped('tb_id')
        wizard = self.env['wizard.tb.po.invoice'].create({'tb_id': bill_id and bill_id[0].id,
                                                          'expense_sheet_id':self.id,
                                                          'type':'expense_po'
                                                          })

        view = self.env.ref('yjzy_extend.wizard_tb_po_form')
        return {
            'name': _(u'创建采购单'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'wizard.tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'new',
            'res_id': wizard.id,
            # 'context': { },
        }
#定
    def create_tb_po_invoice(self):
        self.ensure_one()
        line_tb_id = len(self.expense_line_ids.filtered(lambda x: not x.tb_id))
        if not self.fk_journal_id:
            raise Warning('请先选择付款账户！')
        if line_tb_id != 0:
            raise Warning('有费用明细未选择出运合同！')

        bill_id = self.expense_line_ids.mapped('tb_id')
        tb_po_id = self.env['tb.po.invoice'].create({'tb_id': bill_id and bill_id[0].id,
                                                     'invoice_product_id': self.env.ref('yjzy_extend.product_qtyfk').id,# 0821
                                                     'tax_rate_add':0,
                                                     'expense_tax_algorithm':'multiply',
                                                     'expense_sheet_id':self.id, #1009
                                                     'type':'expense_po',
                                                     'fk_journal_id': self.fk_journal_id.id,
                                                     'bank_id':self.bank_id.id,
                                                     'yjzy_type_1':'purchase',
                                                     'is_tb_hs_id':True,
                                                     })

        view = self.env.ref('yjzy_extend.tb_po_form')
        line_obj = self.env['tb.po.invoice.line']
        extra_invoice_line_obj = self.env['extra.invoice.line']
        for hsl in bill_id.hsname_all_ids:
            line_obj.create({
                'tb_po_id': tb_po_id.id,
                'hs_id': hsl.hs_id.id,
                'hs_en_name': hsl.hs_en_name,
                'purchase_amount2_tax': hsl.purchase_amount2_tax,
                'purchase_amount2_no_tax': hsl.purchase_amount2_no_tax,
                'purchase_amount_max_add_forecast': hsl.purchase_amount_max_add_forecast,
                'purchase_amount_min_add_forecast': hsl.purchase_amount_min_add_forecast,
                'purchase_amount_max_add_rest': hsl.purchase_amount_max_add_rest,
                'purchase_amount_min_add_rest': hsl.purchase_amount_min_add_rest,
                'purchase_back_tax_amount2_new': hsl.purchase_back_tax_amount2_new,
                'hsname_all_line_id': hsl.id,
                'back_tax': hsl.back_tax
            })
        for line in self.expense_line_ids:
            product = line.product_id
            account = product.property_account_income_id
            print('account',account)
            extra_invoice_line_obj.create({
                'tb_po_id': tb_po_id.id,
                'name':'%s' % (product.name),
                'product_id': product.id,
                'quantity': line.quantity,
                'price_unit': line.unit_amount,
                'account_id': account.id

            })
        self.expense_to_invoice_type = 'to_invoice'

        return {
            'name': _(u'创建费用转货款申请'),
            'view_type': 'tree,form',
            "view_mode": 'form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'view_id': view.id,
            'target': 'current',
            'res_id': tb_po_id.id,
            # 'context': { },
        }
    def open_tb_po_invoice(self):
        self.ensure_one()
        bill_id = self.expense_line_ids.mapped('tb_id')
        form_view_id = self.env.ref('yjzy_extend.tb_po_form')
        tree_view_id = self.env.ref('yjzy_extend.tb_po_tree')

        return {
            'name': _(u'费用转采购应付'),
            'view_type': 'form',
            "view_mode": 'tree,form',
            'res_model': 'tb.po.invoice',
            'type': 'ir.actions.act_window',
            'views': [(tree_view_id.id, 'tree'),(form_view_id.id, 'form')],
            'domain': [('id', 'in', [x.id for x in self.tb_po_invoice_ids])],
            'target': 'current'
            # 'context': { },
        }


    @api.onchange('currency_id')
    def onchange_currency_id(self):
        for line in self.expense_line_ids:
            line.currency_id = self.currency_id



 #   @api.onchange('second_categ_id')
   # def onchange_second_categ(self):
  #      for line in self.my_expense_line_ids:
   #         line.categ_id = self.categ_id
   #         line.second_categ_id = self.second_categ_id
   #         line.product_id = False
    #        line.product_id = None
    @api.model
    def update_payment_date_store(self):
        for one in self:
            print('===', one)
            one.payment_date_store = one.payment_id.payment_date_confirm
           # for x in self.expense_line_ids:
            #    x.payment_date_store = self.payment_date_store




    @api.one
    def compute_total_this_year(self):
        now = fields.datetime.now()
        month = now.strftime('%Y-%m-01 00:00:00')
        year = now.strftime('%Y-01-01 00:00:00')



        sql = """select sum(company_currency_total_amount) from hr_expense where state in ('done') and total_amount > 0 and (categ_id != 193 or categ_id is null) and payment_date > '%s' """
        sql_approve = """select sum(company_currency_total_amount) from hr_expense where state in ('confirmed') and (categ_id != 193 or categ_id is null ) and total_amount > 0 """
        sql_submit = """select sum(company_currency_total_amount) from hr_expense where sheet_state in ('submit','approval','employee_approval','account_approval','manager_approval') and (categ_id != 193 or categ_id is null) and total_amount > 0 """
        sql_un_submit = """select sum(company_currency_total_amount) from hr_expense where sheet_state in ('draft','cancel') and (categ_id != 193 or categ_id is null) and total_amount > 0 """

        moth_sql = sql % month
        year_sql = sql % year



        this_sql_approve = sql_approve
        this_sql_submit = sql_submit
        this_sql_un_submit  = sql_un_submit

        print('==', moth_sql)
        print('==', year_sql)
        print('==', this_sql_approve)
        print('==', this_sql_submit)


        self._cr.execute(moth_sql)
        self.total_this_moth = self._cr.fetchall()[0][0]

        self._cr.execute(year_sql)
        self.total_this_year = self._cr.fetchall()[0][0]

        self._cr.execute(this_sql_approve)
        self.total_approve = self._cr.fetchall()[0][0]

        self._cr.execute(this_sql_submit)
        self.total_submit = self._cr.fetchall()[0][0]

        self._cr.execute(this_sql_un_submit)
        self.total_un_submit = self._cr.fetchall()[0][0]





    def compute_my_total_amount(self):
        user = self.env.user

        if user.has_group('yjzy_extend.group_expense_my_total'):
            for one in self:
                my_total_amount = 0.0
                employee_wkf_one = one.employee_wkf
                my_expense_line = one.expense_line_ids.filtered(
                    lambda x: x.employee_id.user_id == user or x.create_uid == user or x.x_tenyale_user_id == user)
                if employee_wkf_one == False: #不等于责任人审批阶段
                    for expense in one.expense_line_ids:
                        my_total_amount += expense.currency_id.with_context(
                            date=expense.date,
                            company_id=expense.company_id.id
                        ).compute(expense.total_amount, one.currency_id)
                        one.my_total_amount = my_total_amount
                        one.my_expense_line_ids = one.expense_line_ids
                        one.my_expense_line_ids_b = one.expense_line_ids
                        one.my_expense_line_ids_employee = one.expense_line_ids
                        one.my_expense_line_ids_company = one.expense_line_ids
                else:
                    for expense in my_expense_line: #如果进入责任人审批阶段
                        my_total_amount += expense.currency_id.with_context(
                            date=expense.date,
                            company_id=expense.company_id.id
                        ).compute(expense.total_amount, one.currency_id)
                        one.my_total_amount = my_total_amount
                        one.my_expense_line_ids =  my_expense_line
                        one.my_expense_line_ids_b =  my_expense_line
                        one.my_expense_line_ids_employee =  my_expense_line
                        one.my_expense_line_ids_company =  my_expense_line
        else:
            for one in self:
                my_total_amount = 0.0
                my_expense_line = one.expense_line_ids.filtered(lambda x: x.employee_id.user_id == user or x.create_uid == user or x.x_tenyale_user_id == user)
                for expense in my_expense_line:
                    my_total_amount += expense.currency_id.with_context(
                        date=expense.date,
                        company_id=expense.company_id.id
                    ).compute(expense.total_amount, one.currency_id)

                    one.my_total_amount = my_total_amount
                    one.my_expense_line_ids = my_expense_line

    @api.depends('expense_line_ids', 'expense_line_ids.is_confirmed')
    def compute_all_line_is_confirmed(self):
        for one in self:
            one.all_line_is_confirmed = one.expense_line_ids and all([x.is_confirmed for x in one.expense_line_ids]) or False

    def create_customer_invoice(self):
        self.ensure_one()
        if self.back_tax_invoice_id:
            return True
        if self.back_tax_amount <= 0:
            return True
        if not self.back_tax_product_id:
            return True

        jounal_obj = self.env['account.invoice'].with_context({'type': 'out_invoice', 'journal_type': 'sale'})
        pdt = self.back_tax_product_id
        partner = self.env.ref('yjzy_extend.partner_back_tax')
        invoice_account = self.env['account.account'].search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        pdt_account = pdt.property_account_income_id

        if not invoice_account:
            raise Warning(u'发票科目 1122 未找到')
        if not pdt:
            raise Warning(u'产品 back_tax1 未找到')
        if not pdt_account:
            raise Warning(u'产品 back_tax1 的科目未设置')

        invoice_line_data = {
            'product': pdt.id,
            'name': pdt.name,
            'account_id': pdt_account.id,
            'price_unit': self.back_tax_amount,
            'product_id': pdt.id,
        }
        invoice_id = jounal_obj.create({
            'name': u'草稿发票',
            'partner_id': partner.id,
            'account_id': invoice_account.id,
            'invoice_line_ids': [(0, 0, invoice_line_data)],
            'gongsi_id': self.gongsi_id.id,
        })
        self.back_tax_invoice_id = invoice_id

    def create_other_payment_invoice(self):
        self.ensure_one()
        if self.other_payment_invoice_id:
            return True
        if self.other_payment_invoice_amount <= 0:
            return True
        if not self.other_payment_invoice_product_id:
            return True

        jounal_obj = self.env['account.invoice'].with_context({'type': 'out_invoice', 'journal_type': 'sale'})
        pdt = self.other_payment_invoice_product_id
        partner = self.partner_id
        invoice_account = self.env['account.account'].search([('code', '=', '1122'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        pdt_account = pdt.property_account_income_id

        if not invoice_account:
            raise Warning(u'发票科目 1122 未找到')
        if not pdt:
            raise Warning(u'请填写其他应收项目')
        if not pdt_account:
            raise Warning(u'请填写其他应收项目的科目未设置')

        invoice_line_data = {
            'product': pdt.id,
            'name': pdt.name,
            'account_id': pdt_account.id,
            'price_unit': self.other_payment_invoice_amount,
            'product_id': pdt.id,
        }
        invoice_id = jounal_obj.create({
            'name': u'草稿发票',
            'partner_id': partner.id,
            'account_id': invoice_account.id,
            'invoice_attribute': 'other_payment',
            'yjzy_type_1': 'sale',
            'journal_type': 'sale',
            'date': fields.datetime.now(),
            'date_invoice': fields.datetime.now(),
            'type': 'out_invoice',
            'invoice_line_ids': [(0, 0, invoice_line_data)],
            'gongsi_id': self.gongsi_id.id,
        })
        self.other_payment_invoice_id = invoice_id




    @api.onchange('payment_id')
    def onchange_payment_id(self):
        ctx = self.env.context
        default_bank_journal_code = ctx.get('default_bank_journal_code', '')
        if default_bank_journal_code == 'ysdrl':
            self.currency_id = self.payment_id.currency_id




    def create_rcfkd(self):
        amount = self.total_amount
        account_code = amount > 0 and '112301' or '220301'
        sfk_type = amount > 0 and 'rcfkd' or 'rcskd'
        ctx = {'default_sfk_type': sfk_type}
        advance_account = self.env['account.account'].search([('code', '=', account_code),('company_id', '=', self.company_id.id)], limit=1)


        if not self.fk_journal_id.currency_id:
            raise Warning(u'没有取到付款日记账的货币，请检查设置')
        if not advance_account:
            raise Warning(u'没有找到对应的预处理科目%s' % account_code)

        payment = self.env['account.payment'].with_context(ctx).create({
            'sfk_type': amount > 0 and 'rcfkd' or 'rcskd',
            'payment_type': amount > 0 and 'outbound' or 'inbound',
            'partner_id': self.partner_id.id,
            'partner_type': amount > 0 and 'supplier' or 'customer',
            'fybg_ids': [(6, 0, [self.id])],
            'journal_id': self.fk_journal_id.id,
            'currency_id': self.fk_journal_id.currency_id.id,
            'amount': abs(amount),
            'payment_method_id': 2,
            'advance_ok': True,
            'advance_account_id': advance_account.id,
            'bank_id': self.bank_id.id,
            'include_tax': self.include_tax,
            'gongsi_id': self.gongsi_id.id,
        })
        self.payment_id = payment
        for one in self.expense_line_ids:
            one.state = 'confirmed'


    @api.multi
    def unlink(self):
        lines = self.mapped('expense_line_ids')
        lines.unlink()
        for one in self:
            if one.state not in ('cancel', 'draft'):
                raise Warning(u'只有草稿或者拒绝状态允许删除')
            attachments = self.env['ir.attachment'].search([('res_model', '=', one._name), ('res_id', '=', one.id)])
            attachments.unlink()
            if attachments and (not (one.state in ['draft', 'cancel'])):
                raise Warning('费用报告 审批中禁止删除附件')

        return super(hr_expense_sheet, self).unlink()



    @api.model
    def _cron_approve(self, domain_str='[]', trans_id=None):
        domain = eval(domain_str)
        for one in self.search(domain):
            one.with_context(trans_id=trans_id, no_pop=True).wkf_button_action()


    def action_to_account_approval_all(self):
        stage_id = self._stage_find(domain=[('code', '=', '030')])
        for one in self:
            if one.expense_to_invoice_type == 'normal' and one.all_line_is_confirmed == True and one.total_amount >= 0 and one.state_1 == 'employee_approval':
                one.write({'employee_wkf':False,
                            'stage_id': stage_id.id,
                            })


    @api.multi
    def post_message_lines(self, message):
        for expense in self.expense_line_ids:
            expense.message_post(body=message, subject=None, message_type='notification',
                                 subtype=None, parent_id=None, attachments=None,
                                 content_subtype='html')

    def add_line_message_followers(self):
        for expense in self.expense_line_ids:
            expense.message_subscribe(partner_ids=[expense.user_id.partner_id.id])

    def btn_user_confirm(self):
        self.expense_line_ids.btn_user_confirm()

    def btn_undo_confirm(self):
        self.expense_line_ids.btn_undo_confirm()

    def btn_undo_confirm_force(self):
        self.expense_line_ids.btn_undo_confirm_force()

    def btn_match_budget(self):
        self.expense_line_ids.match_budget()

        self.is_budget = True

    def btn_release_budget(self):
        self.expense_line_ids.release_budget()
        self.is_budget = False



