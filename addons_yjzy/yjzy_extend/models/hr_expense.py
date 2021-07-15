# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, float_compare

from odoo.addons import decimal_precision as dp


class hr_expense(models.Model):
    _inherit = 'hr.expense'

    _cache_categ = {}
    _cache_second_categ = {}

    @api.model
    def default_categ(self):
        return self._cache_categ.get(self._uid)

    @api.model
    def default_second_categ(self):
        return self._cache_second_categ.get(self._uid)

    def compute_balance(self):
        # 余额：当科目余额 = 贷方，外币的时候：负外币金额之和，本币的时候：贷方和 - 借方和 。 如果没有选择借贷方，则不进行计算
        for one in self:
            if one.hx_code:
                account = one.account_id
                move_lines = self.env['account.move.line'].search(
                    [('hx_code', '=', one.hx_code), ('account_id', '=', account.id)])
                if account.polarity:
                    if one.currency_id.name != 'CNY':
                        one.hx_balance = sum([x.amount_currency for x in move_lines]) * account.polarity
                    else:
                        one.hx_balance = sum([x.debit - x.credit for x in move_lines]) * account.polarity

                if one.unit_amount > 0:
                    one.diff_balance = one.hx_balance - one.unit_amount
                elif one.unit_amount < 0:
                    one.diff_balance = one.hx_balance + one.unit_amount
                else:
                    pass

    @api.depends('currency_id', 'total_amount', 'company_currency_id')
    def compute_total_amount_currency(self):
        # self.ensure_one() 只需要计算一条记录
        for one in self:
            total_currency_amount = one.currency_id.compute(one.total_amount, one.company_currency_id)
            one.company_currency_total_amount = total_currency_amount

    @api.model
    def default_hx_code(self):
        return self.env['ir.sequence'].next_by_code('hx.code')

    @api.depends('sheet_id', 'sheet_id.expense_to_invoice_type')
    def _compute_expense_to_invoice_type(self):
        for one in self:
            expense_to_invoice_type = one.sheet_id.expense_to_invoice_type
            one.expense_to_invoice_type = expense_to_invoice_type

    @api.depends('sheet_id', 'sheet_id.stage_id')
    def compute_stage_id(self):
        for one in self:
            stage_id = one.sheet_id.stage_id
            one.stage_id = stage_id

    expense_to_invoice_type = fields.Selection([('normal', u'常规费用'),
                                                ('to_invoice', u'转为货款'),
                                                ('other_payment', u'其他支出'),
                                                ('incoming', u'其他收入')], u'类型说明',
                                               compute=_compute_expense_to_invoice_type,
                                               store=True)  # related='sheet_id.expense_to_invoice_type'

    sheet_id = fields.Many2one('hr.expense.sheet', string="费用报告", readonly=True, copy=False, ondelete="cascade")

    stage_id = fields.Many2one('expense.sheet.stage', u'审批流', compute=compute_stage_id, store=True)
    state_1 = fields.Selection([('draft', u'草稿'),
                                ('employee_approval', u'待责任人确认'),
                                ('account_approval', u'待财务审批'),
                                ('manager_approval', u'待总经理审批'),
                                ('post', u'审批完成待支付'),
                                ('done', u'完成'),
                                ('refused', u'已拒绝'),
                                ('cancel', u'取消'),
                                ], u'报告审批状态', related='stage_id.state')
    include_tax = fields.Boolean(u'含税')
    line_ids = fields.One2many('hr.expense.line', 'expense_id', u'分配明细')
    # user_ids = fields.Many2many('res.users', compute=compute_line_user, string='用户s', store=True)

    state = fields.Selection([
        ('done', 'Posted'),
        ('draft', 'To Submit'),
        ('reported', 'Reported'),
        ('employee_confirm', '责任人确认'),
        ('confirmed', u'已经确认'),
        ('refused', 'Refused'),
    ], compute='_compute_state', string='Status', copy=False, index=True, readonly=True, store=True,
        help="Status of the expense.")
    user_id = fields.Many2one('res.users', related='employee_id.user_id', readonly=True, string=u'用户',
                              track_visibility='onchange')
    tb_ids = fields.Many2many('transport.bill', 'ref_bill_expense', 'eid', 'bid', u'出运单')
    tb_id = fields.Many2one('transport.bill', u'出运合同')
    tb_approve_date = fields.Date(u'审批完成时间', related='tb_id.approve_date', store=True, readonly=True)
    tb_budget = fields.Monetary('出运单预算', related='tb_id.budget_amount', currency_field='currency_id')
    tb_budget_rest = fields.Monetary('出运单预算剩余', related='tb_id.budget_reset_amount', currency_field='currency_id')

    yjzy_payment_id = fields.Many2one('account.payment', u'新付款单', related='sheet_id.payment_id', store=True)
    fkzl_id = fields.Many2one('account.payment', u'付款指令', related='sheet_id.fkzl_id', store=True)
    yjzy_payment_currency_id = fields.Many2one('res.currency', u'新付款单币种', related='yjzy_payment_id.currency_id')
    balance = fields.Monetary(related='yjzy_payment_id.balance', currency_field='yjzy_payment_currency_id')

    negative_unit_amount = fields.Monetary(u'负数金额', currency_field='currency_id')
    negative_total_amount = fields.Monetary(u'负数总计', currency_field='currency_id')

    partner_id = fields.Many2one('res.partner', related='sheet_id.partner_id', readonly=True, string=u'付款对象')

    hx_expense_id = fields.Many2one('hr.expense', u'核销费用')
    hx_code = fields.Char(u'内部核对标记', default=lambda self: self.default_hx_code())
    hx_balance = fields.Monetary('内部核对余额', compute=compute_balance, currency_field='currency_id')
    diff_balance = fields.Monetary('内部核对差额', compute=compute_balance, currency_field='currency_id')

    diff_expense = fields.Monetary('差额费用', currency_field='currency_id')
    diff_product_id = fields.Many2one('product.product', u'差额产品')

    is_confirmed = fields.Boolean('责任人已确认', readonly=True)

    ask_uid = fields.Many2one('res.users', u'费用申请人')
    sheet_employee_id = fields.Many2one('hr.employee', u'报告申请人', related='sheet_id.employee_id', readonly=True)

    categ_id = fields.Many2one('product.category', '大类', default=default_categ)
    second_categ_id = fields.Many2one('product.category', '中类', default=default_second_categ)

    sheet_wkf_state = fields.Selection(string='报告工作流状态', related='sheet_id.x_wkf_state', readonly=True)

    document_number_1 = fields.Integer(u'单据数量')

    account_confirm_uid = fields.Many2one('res.users', u'财务审批')

    manager_confirm_uid = fields.Many2one('res.users', u'总经理审批')

    sheet_state = fields.Selection(string='报告状态', related='sheet_id.state', readonly=True, store=True)

    user_budget_id = fields.Many2one('user.budget', '人员年度预算')
    user_budget_amount = fields.Monetary('人员年度预算金额', related='user_budget_id.amount', currency_field='currency_id')
    user_budget_amount_reset = fields.Monetary('人员年度预算剩余', related='user_budget_id.amount_reset',
                                               currency_field='currency_id')

    employee_confirm_date = fields.Date(u'责任人确认日期')
    employee_confirm_name = fields.Char(u'责任人确认')
    employee_confirm_user = fields.Many2one('res.users', u'责任人确认')

    company_budget_id = fields.Many2one('company.budget', '公司年度预算')
    company_budget_amount = fields.Monetary('公司年度预算金额', related='company_budget_id.amount',
                                            currency_field='currency_id')
    company_budget_amount_reset = fields.Monetary('公司年度预算剩余', related='company_budget_id.amount_reset',
                                                  currency_field='currency_id')

    sheet_all_line_is_confirmed = fields.Boolean('责任人全部确认', related='sheet_id.all_line_is_confirmed')

    payment_date = fields.Date(u'付款日期', related='sheet_id.accounting_date', store=True)
    sheet_name = fields.Date(u'费用说明', related='sheet_id.name', store=True, readonly=True)

    sheet_employee_confirm_date = fields.Date(u'申请人确认日期', related='sheet_id.employee_confirm_date', readonly=True)
    sheet_employee_confirm = fields.Many2one('res.users', u'申请人确认', related='sheet_id.employee_confirm', readonly=True)

    sheet_account_confirm_date = fields.Date('财务审批日期', related='sheet_id.account_confirm_date', readonly=True)
    sheet_account_confirm = fields.Many2one('res.users', u'财务审批', related='sheet_id.account_confirm', readonly=True)

    sheet_manager_confirm = fields.Many2one('res.users', u'总经理审批', related='sheet_id.manager_confirm', readonly=True)
    sheet_manager_confirm_date = fields.Date('总经理审批日期', related='sheet_id.manager_confirm_date', readonly=True)

    lead_id = fields.Many2one('crm.lead', '项目编号')
    sys_outer_hetong = fields.Char('系统外合同')

    budget_id = fields.Many2one('budget.budget', '预算')
    budget_amount = fields.Monetary('预算金额', related='budget_id.amount', currency_field='company_currency_id',
                                    readonly=True)
    budget_amount_reset = fields.Monetary('预算剩余', related='budget_id.amount_reset',
                                          currency_field='company_currency_id', readonly=True)
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    budget_expense_list_ids = fields.One2many('hr.expense', '预算明细', related='budget_id.expense_ids', readonly=True)

    employee_sales_uid = fields.Many2one('hr.employee',
                                         '费用对象')  # , default=lambda self: self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
    budget_type = fields.Selection("预算类型", related="categ_id.budget_type")
    # akiny
    is_onchange_false = fields.Boolean('是否onchange')
    is_onchange_false1 = fields.Boolean('是否onchange')
    company_currency_id = fields.Many2one('res.currency', u'公司货币',
                                          default=lambda self: self.env.user.company_id.currency_id.id)
    company_currency_total_amount = fields.Monetary(u'本币合计', currency_field='company_currency_id',
                                                    compute=compute_total_amount_currency, digits=(2, 4), store=True)

    user_menu_id = fields.Many2one('user.menu', u'看板记录')

    # payment_date_store = fields.Datetime(u'付款日期')

    def open_budget(self):
        form_view = self.env.ref('yjzy_extend.budget_budget_form')
        return {
            'name': u'项目预算表',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'budget.budget',
            'type': 'ir.actions.act_window',
            'views': [(form_view.id, 'form')],
            'res_id': self.budget_id.id,
            'target': 'new',
            'flags': {'form': {'initial_mode': 'view', 'action_buttons': False}},
            'context': {'open': 1}
        }

    @api.model
    def update_payment_date_store(self):
        for one in self:
            print('===', one)
            one.payment_date = one.sheet_id.accounting_date

    # def update_feiyongduixiang(self):
    #   for one in self:
    #       print('===', one)
    #      if one.employee_id.employee_sales_uid:
    #        one.employee_sales_uid = one.employee_id.employee_sales_uid

    def open_expense_form(self):
        view = self.env.ref('yjzy_extend.view_hr_expense_line_form')
        return {
            'type': 'ir.actions.act_window',
            'name': u'费用明细',
            'view_type': 'form',
            'view_mode': 'form',
            'views': [(view.id, 'form')],
            'res_model': self._name,
            'res_id': self.id,
            'target': 'new',
        }

    @api.multi
    def action_save_test(self):
        # your code
        self.ensure_one()
        # close popup
        return {'type': 'ir.actions.act_window_close'}

    def get_budget_type(self):
        return self.second_categ_id.budget_type or self.categ_id.budget_type or None

    def release_budget(self):
        for one in self:
            one.budget_id = False

    def match_budget(self):
        budget_obj = self.env['budget.budget']
        date = fields.date.today()
        for one in self:
            no_match = False
            categ = one.second_categ_id.budget_type and one.second_categ_id or one.categ_id
            dm = [('categ_id', '=', categ.id), ('date_start', '<', date), ('date_end', '>=', date)]
            if categ.budget_type:
                if categ.budget_type == 'employee':
                    dm += [('employee_id', '=', one.employee_id.id)]
                elif categ.budget_type == 'transport':
                    if one.tb_id:
                        dm = [('tb_id', '=', one.tb_id.id)]
                    else:
                        continue

                elif categ.budget_type == 'lead':
                    if one.lead_id:
                        dm = [('lead_id', '=', one.lead_id.id)]
                    else:
                        continue

            budget = budget_obj.search(dm)
            if len(budget) > 1:
                raise Warning('匹配到多个预算记录，请联系管理员')
            if budget:
                one.budget_id = budget

    # @api.onchange('categ_id')
    # def onchange_categ(self):
    #     if self.is_onchange_false:
    #        self.second_categ_id = False
    #     else:
    #         if self.categ_id:
    #            self._cache_categ.update({self._uid: self.categ_id.id})
    #            self.is_onchange_false = True
    @api.onchange('categ_id')
    def onchange_categ(self):
        a = 0
        if self.categ_id.id != self._cache_categ.get(self._uid):
            print('test_onchange', self.categ_id, self._cache_categ.get(self._uid))
            self.second_categ_id = False
            self._cache_categ.update({self._uid: self.categ_id.id})

    #
    # @api.onchange('second_categ_id')
    # def onchange_second_categ(self):
    #     if self.is_onchange_false1:
    #        self.product_id = False
    #     else:
    #         if self.second_categ_id:
    #            self._cache_second_categ.update({self._uid: self.second_categ_id.id})
    #            self.is_onchange_false1 = True

    @api.onchange('second_categ_id')
    def onchange_second_categ(self):
        self.product_id = False
        self._cache_second_categ.update({self._uid: self.second_categ_id.id})

    @api.onchange('employee_id')
    # akiny只有是客户经理的时候才跟着责任人变化

    def onchange_employee_id(self):
        self.employee_sales_uid = self.employee_id.employee_sales_uid

    # job_id_name = self.employee_id.job_id.name

    # if job_id_name == u'客户经理':
    #    self.employee_sales_uid = self.employee_id
    # else:
    #     if job_id_name == u'业务助理':
    #        self.employee_sales_uid = self.user_id.assistant_id.employee_id
    #     else:
    #         self.employee_sales_uid = None

    def btn_user_confirm(self):
        force = self.env.context.get('force')
        for one in self:
            if force:
                one.is_confirmed = True
                one.state = 'employee_confirm'
                one.employee_confirm_date = fields.datetime.now()
                one.employee_confirm_name = self.env.user.name
                one.employee_confirm_user = self.env.user.id
            else:
                if one.user_id == self.env.user:
                    one.is_confirmed = True
                    one.state = 'employee_confirm'
                    one.employee_confirm_date = fields.datetime.now()
                    one.employee_confirm_name = self.env.user.name
                    one.employee_confirm_user = self.env.user.id
                    if one.sheet_id.expense_to_invoice_type == 'normal' and one.sheet_id.all_line_is_confirmed == True and one.sheet_id.total_amount >= 0 and one.sheet_id.state_1 == 'employee_approval':
                        one.sheet_id.sudo().action_to_account_approval_all()

    def btn_undo_confirm_force(self):
        return self.with_context(force=True).btn_undo_confirm()

    def btn_undo_confirm(self):
        force = self.env.context.get('force')
        for one in self:
            if force:
                one.is_confirmed = False
                # akiny
                one.state = 'reported'
                one.employee_confirm_date = False
                one.employee_confirm_name = False
                one.employee_confirm_user = False
            else:
                if one.user_id == self.env.user:
                    one.is_confirmed = False
                    one.state = 'reported'
                    one.employee_confirm_date = False
                    one.employee_confirm_name = False
                    one.employee_confirm_user = False

    def action_employee_confirm(self):
        self.ensure_one()
        ##if self.user_id != self.env.user:
        if self.user_id == self.env.user:
            if self.categ_id.name == '订单费用' and self.tb_id == False:
                raise Warning('订单费用必须填写出运合同号!')
            self.is_confirmed = True
            self.state = 'employee_confirm'
            self.employee_confirm_date = fields.datetime.now()
            self.employee_confirm_name = self.env.user.name
            self.employee_confirm_user = self.env.user.id
            if self.sheet_id.expense_to_invoice_type == 'normal' and self.sheet_id.all_line_is_confirmed == True and self.sheet_id.total_amount >= 0 and self.sheet_id.state_1 == 'employee_approval':
                self.sheet_id.sudo().action_to_account_approval_all()
        else:
            raise Warning('必须是责任人自己')

    def make_diff_mvoe(self):
        if not self.diff_expense:
            return True

        aml_ob = self.env['account.move.line'].with_context(check_move_validity=False)
        account = self.account_id
        polarity = account.polarity

        if not polarity:
            raise Warning(u'科目没有设置借贷方向')

        journal = self.env['account.journal'].search(
            [('code', '=', '杂项'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
        if not journal:
            raise Warning(u'没有找到对应的日记账')

        move = self.env['account.move'].create({
            'journal_id': journal.id,
            'company_id': self.env.user.company_id.id,
            'date': fields.datetime.now(),
            'ref': self.name,
            'name': '/',
        })

        debit_move, credit_move = self.prepare_diff_account_move_line(move)
        aml_ob.create(debit_move)
        aml_ob.create(credit_move)

        print(move)

        return move

    def prepare_diff_account_move_line(self, move):
        """

        如果余额方向 = 借方，点差额处理：生成分录：
        借：差额费用产品对应的科目
        贷：product_id对应的科目（也就是原单据
        我们计算余额的那个产品科目）

        如果余额方向 = 贷方，点差额处理：生成分录：
        借：product_id对应的科目（也就是原单据
        我们计算余额的那个产品科目）
        贷：差额费用对应的科目
        """
        account = self.account_id
        polarity = account.polarity

        diff_product_account = self.diff_product_id.property_account_expense_id

        if polarity == 1:
            if not diff_product_account:
                raise Warning(u'差额产品没用定义费用科目')
            debit_move = {
                'move_id': move.id,
                'type': 'dest',
                'name': '>0差额费用:借',
                'account_id': diff_product_account.id,
                'currency_id': self.currency_id.id,
                'debit': self.diff_expense,
                'expense_id': self.id,
            }
            credit_move = {
                'move_id': move.id,
                'type': 'dest',
                'name': '>0差额费用:贷',
                'account_id': self.account_id.id,
                'currency_id': self.currency_id.id,
                'credit': self.diff_expense,
                'expense_id': self.id,
            }
        elif polarity == -1:
            debit_move = {
                'move_id': move.id,
                'type': 'dest',
                'name': '<0差额费用:借',
                'account_id': self.account_id.id,
                'currency_id': self.currency_id.id,
                'debit': self.diff_expense,
                'expense_id': self.id,

            }
            credit_move = {
                'move_id': move.id,
                'type': 'dest',
                'name': '<0差额费用:贷',
                'account_id': diff_product_account.id,
                'currency_id': self.currency_id.id,
                'credit': self.diff_expense,
                'expense_id': self.id,
            }
        return debit_move, credit_move

    @api.onchange('hx_expense_id')
    def onchange_hx_expense(self):
        if self.hx_expense_id:
            self.hx_code = self.hx_expense_id.hx_code

    def make_hx_code(self):
        self.hx_code = self.env['ir.sequence'].next_by_code('hx.code')

    def init_tb_id(self):
        for one in self.search([]):
            if one.tb_ids and (not one.tb_id):
                one.write({'tb_id': one.tb_ids[0].id})
        return True

    @api.onchange('negative_unit_amount')
    def onchange_negative_unit_amount(self):
        self.unit_amount = self.negative_unit_amount * -1
        self.negative_total_amount = self.total_amount * -1

    @api.model
    def create(self, vals):
        x = super(hr_expense, self.with_context({'tracking_disable': True}))
        return x.create(vals)

    def check_user(self):
        self.ensure_one()
        return self.employee_id.user_id == self.env.user

    def check_leader(self):
        self.ensure_one()
        res = self.employee_id.parent_id.user_id == self.env.user
        return res

    def sheet_action(self, trans_id):
        self.sheet_id.with_context(trans_id=trans_id, no_pop=True).wkf_button_action()


class hr_expense_line(models.Model):
    _name = 'hr.expense.line'
    _order = 'user_id'

    expense_id = fields.Many2one('hr.expense', u'费用')
    user_id = fields.Many2one('res.users', u'用户', required=True)
    amount = fields.Float(u'金额')
    state = fields.Selection([('draft', u'待确认'), ('confirmed', u'已确认')], u'状态', default='draft')

    def user_confirm(self):
        self.ensure_one()
        if self.env.user != self.user_id:
            raise Warning(u'必须是本人确认')
        if self.amount <= 0:
            raise Warning(u'金额不能小于等于0')
        self.state = 'confirmed'
