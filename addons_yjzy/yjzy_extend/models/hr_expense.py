# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from odoo.tools import float_is_zero, float_compare

from odoo.addons import decimal_precision as dp


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

    def _compute_negative_total_amount(self):
        for one in self:
            one.negative_total_amount = -1 * one.total_amount

    def _default_back_tax_product(self):
        try:
            return self.env.ref('yjzy_extend.product_back_tax').id
        except Exception as e:
            return None

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

    negative_total_amount = fields.Monetary(u'负数总计', currency_field='currency_id', compute=_compute_negative_total_amount)

    back_tax_product_id = fields.Many2one('product.product', u'退税产品', domain=[('type', '=', 'service')], default=_default_back_tax_product)
    back_tax_amount = fields.Monetary(u'退税金额')
    back_tax_invoice_id = fields.Many2one('account.invoice', u'退税发票')

    all_line_is_confirmed = fields.Boolean('责任人已全部确认', compute='compute_all_line_is_confirmed')

    document_number = fields.Integer(u'单据数量')
    account_confirm_uid = fields.Many2one('res.users', u'财务审批')

    manager_confirm_uid = fields.Many2one('res.users', u'总经理审批')

    my_total_amount = fields.Float(string='权限金额', compute='compute_my_total_amount', digits=dp.get_precision('Account'))
    my_expense_line_ids = fields.One2many('hr.expense', compute='compute_my_total_amount', string='权限明细')

    total_this_moth = fields.Float(u'本月费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    total_this_year = fields.Float(u'今年费用', compute='compute_total_this_year', digits=dp.get_precision('Account'))
    employee_wkf = fields.Boolean('责任人阶段')
    # akiny 审批确认信息记录
    employee_confirm_date = fields.Date('申请人确认日期')
    employee_confirm = fields.Many2one('res.users', u'申请人确认')

    account_confirm_date = fields.Date('财务审批日期')
    account_confirm = fields.Many2one('res.users', u'财务审批')

    manager_confirm = fields.Many2one('res.users', u'总经理审批')
    manager_confirm_date = fields.Date('总经理审批日期')
    state = fields.Selection(selection_add=[('approved', u'批准'), ('approval', u'审批中'), ('Approval', u'审批历史消息')])

    categ_id = fields.Many2one('product.category', '大类')
    second_categ_id = fields.Many2one('product.category', '中类')

    @api.onchange('categ_id')
    def onchange_categ(self):
        self.second_categ_id = None

    @api.one
    def compute_total_this_year(self):
        now = fields.datetime.now()
        month = now.strftime('%Y-%m-01 00:00:00')
        year = now.strftime('%Y-01-01 00:00:00')

        sql = """select sum(total_amount) from hr_expense_sheet where state in ('approve','post','done') and create_date > '%s'  """

        moth_sql = sql % month
        year_sql = sql % year

        print('==', moth_sql)
        print('==', year_sql)

        self._cr.execute(moth_sql)
        self.total_this_moth = self._cr.fetchall()[0][0]

        self._cr.execute(year_sql)
        self.total_this_year = self._cr.fetchall()[0][0]

    def compute_my_total_amount(self):
        user = self.env.user

        if user.has_group('yjzy_extend.group_expense_my_total'):
            for one in self:
                my_total_amount = 0.0
                employee_wkf_one = one.employee_wkf
                my_expense_line = one.expense_line_ids.filtered(
                    lambda x: x.employee_id.user_id == user or x.create_uid == user or x.x_tenyale_user_id == user)
                if employee_wkf_one == False:
                    for expense in one.expense_line_ids:
                        my_total_amount += expense.currency_id.with_context(
                            date=expense.date,
                            company_id=expense.company_id.id
                        ).compute(expense.total_amount, one.currency_id)
                        one.my_total_amount = my_total_amount
                        one.my_expense_line_ids = one.expense_line_ids
                else:
                    for expense in my_expense_line:
                        my_total_amount += expense.currency_id.with_context(
                            date=expense.date,
                            company_id=expense.company_id.id
                        ).compute(expense.total_amount, one.currency_id)
                        one.my_total_amount = my_total_amount
                        one.my_expense_line_ids = one.expense_line_ids
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
            'invoice_line_ids': [(0, 0, invoice_line_data)]
        })
        self.back_tax_invoice_id = invoice_id

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
        advance_account = self.env['account.account'].search([('code', '=', account_code)], limit=1)

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
        })
        self.payment_id = payment

    @api.multi
    def unlink(self):
        lines = self.mapped('expense_line_ids')
        lines.unlink()
        return super(hr_expense_sheet, self).unlink()

    def unlink(self):
        for one in self:
            if one.state not in ('cancel', 'draft'):
                raise Warning(u'只有草稿或者拒绝状态允许删除')

        return super(hr_expense_sheet, self).unlink()

    @api.model
    def _cron_approve(self, domain_str='[]', trans_id=None):
        domain = eval(domain_str)
        for one in self.search(domain):
            one.with_context(trans_id=trans_id, no_pop=True).wkf_button_action()

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

    def btn_match_budget(self):
        self.expense_line_ids.match_budget()
    # def btn_company_budget(self):
    #     self.my_expense_line_ids.btn_company_budget()
    #
    # def btn_user_budget(self):
    #     self.my_expense_line_ids.btn_user_budget()



class hr_expense(models.Model):
    _inherit = 'hr.expense'

    # @api.depends('line_ids')
    # def compute_line_user(self):
    #     for one in self:
    #         one.user_ids = one.line_ids.mapped('user_id')

    def compute_balance(self):
        # 余额：当科目余额 = 贷方，外币的时候：负外币金额之和，本币的时候：贷方和 - 借方和 。 如果没有选择借贷方，则不进行计算
        for one in self:
            if one.hx_code:
                account = one.account_id
                move_lines = self.env['account.move.line'].search([('hx_code', '=', one.hx_code), ('account_id', '=', account.id)])
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

    @api.model
    def default_hx_code(self):
        return self.env['ir.sequence'].next_by_code('hx.code')

    include_tax = fields.Boolean(u'含税')
    line_ids = fields.One2many('hr.expense.line', 'expense_id', u'分配明细')
    # user_ids = fields.Many2many('res.users', compute=compute_line_user, string='用户s', store=True)
    state = fields.Selection(selection_add=[('confirmed', u'已经确认'), ('employee_confirm', '责任人确认')])
    user_id = fields.Many2one('res.users', related='employee_id.user_id', readonly=False, string=u'用户', track_visibility='onchange')
    tb_ids = fields.Many2many('transport.bill', 'ref_bill_expense', 'eid', 'bid', u'出运单')
    tb_id = fields.Many2one('transport.bill', u'出运合同')
    tb_budget = fields.Monetary('出运单预算', related='tb_id.budget_amount', currency_field='currency_id')
    tb_budget_rest = fields.Monetary('出运单预算剩余', related='tb_id.budget_reset_amount', currency_field='currency_id')

    yjzy_payment_id = fields.Many2one('account.payment', u'新付款单', related='sheet_id.payment_id', store=True)
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

    categ_id = fields.Many2one('product.category', '大类')
    second_categ_id = fields.Many2one('product.category', '中类')

    sheet_wkf_state = fields.Selection(string='报告工作流状态', related='sheet_id.x_wkf_state', readonly=True)

    document_number_1 = fields.Integer(u'单据数量')

    account_confirm_uid = fields.Many2one('res.users', u'财务审批')

    manager_confirm_uid = fields.Many2one('res.users', u'总经理审批')

    sheet_state = fields.Selection(string='报告状态', related='sheet_id.state', readonly=True, store=True)

    user_budget_id = fields.Many2one('user.budget', '人员年度预算')
    user_budget_amount = fields.Monetary('人员年度预算金额', related='user_budget_id.amount', currency_field='currency_id')
    user_budget_amount_reset = fields.Monetary('人员年度预算剩余', related='user_budget_id.amount_reset', currency_field='currency_id')

    employee_confirm_date = fields.Date(u'责任人确认日期')
    employee_confirm_name = fields.Char(u'责任人确认')
    employee_confirm_user = fields.Many2one('res.users', u'责任人确认')

    company_budget_id = fields.Many2one('company.budget', '公司年度预算')
    company_budget_amount = fields.Monetary('公司年度预算金额', related='company_budget_id.amount', currency_field='currency_id')
    company_budget_amount_reset = fields.Monetary('公司年度预算剩余', related='company_budget_id.amount_reset', currency_field='currency_id')

    sheet_all_line_is_confirmed = fields.Boolean('责任人全部确认', related='sheet_id.all_line_is_confirmed')

    payment_date = fields.Datetime(u'付款日期', related='sheet_id.payment_id.payment_date_confirm')

    sheet_employee_confirm_date = fields.Date(u'申请人确认日期', related='sheet_id.employee_confirm_date', readonly=True)
    sheet_employee_confirm = fields.Many2one('res.users', u'申请人确认', related='sheet_id.employee_confirm', readonly=True)

    sheet_account_confirm_date = fields.Date('财务审批日期', related='sheet_id.account_confirm_date', readonly=True)
    sheet_account_confirm = fields.Many2one('res.users', u'财务审批', related='sheet_id.account_confirm', readonly=True)

    sheet_manager_confirm = fields.Many2one('res.users', u'总经理审批', related='sheet_id.manager_confirm', readonly=True)
    sheet_manager_confirm_date = fields.Date('总经理审批日期', related='sheet_id.manager_confirm_date', readonly=True)

    lead_id = fields.Many2one('crm.lead', '项目编号')
    sys_outer_hetong = fields.Char('系统外合同')

    budget_id = fields.Many2one('budget.budget', '预算')
    budget_amount = fields.Monetary('预算金额', related='budget_id.amount', currency_field='currency_id', readonly=True)
    budget_amount_reset = fields.Monetary('预算剩余', related='budget_id.amount_reset', currency_field='currency_id', readonly=True)


    def get_budget_type(self):
        return self.second_categ_id.budget_type or self.categ_id.budget_type or None

    def match_budget(self):
        budget_obj = self.env['budget.budget']
        date = fields.date.today()
        for one in self:
            budget_type = one.get_budget_type()
            if not budget_type:
                raise Warning('没有匹配到费用类型，请检查中类和大类的设置')

            dm = [('type', '=', budget_type), ('date_start', '<', date), ('date_end', '>=', date)]

            budget = budget_obj.search(dm)
            if len(budget) > 1:
                raise Warning('匹配到多个预算记录，请联系管理员')
            if budget:
                one.budget_id = budget


    # def btn_company_budget(self):
    #     budget_obj = self.env['company.budget']
    #     date = fields.date.today()
    #     for one in self:
    #         if one.categ_id.is_company_budget:
    #             budget = budget_obj.search([('type', '=', 'month'), ('date_start', '<', date), ('date_end', '>=', date)], limit=1)
    #             if budget:
    #                 one.company_budget_id = budget
    #
    # def btn_user_budget(self):
    #     budget_obj = self.env['user.budget']
    #     date = fields.date.today()
    #     for one in self:
    #         print('==', one.categ_id.is_user_budget, one.employee_id.name, date)
    #         if one.categ_id.is_user_budget:
    #             budget = budget_obj.search([('employee_id', '=', one.employee_id.id), ('date_start', '<', date), ('date_end', '>=', date)], limit=1)
    #             if budget:
    #                 one.user_budget_id = budget


    # @api.onchange('categ_id')
    # def onchange_categ(self):
    #     self.second_categ_id = None
    #     self.product_id = None

    @api.onchange('second_categ_id')
    def onchange_second_categ(self):
        self.product_id = None

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
            self.is_confirmed = True
            self.state = 'employee_confirm'
            self.employee_confirm_date = fields.datetime.now()
            self.employee_confirm_name = self.env.user.name
            self.employee_confirm_user = self.env.user.id
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

        journal = self.env['account.journal'].search([('code', '=', '杂项'), ('company_id', '=', self.env.user.company_id.id)], limit=1)
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
