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


    @api.depends('currency_id', 'total_amount', 'company_currency_id')
    def compute_total_amount_currency(self):
        # self.ensure_one() 只需要计算一条记录
        for one in self:
            total_currency_amount = one.currency_id.compute(one.total_amount, one.company_currency_id)
            one.company_currency_total_amount = total_currency_amount


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
    gongsi_id = fields.Many2one('gongsi', '内部公司')

    #akiny
    is_budget = fields.Boolean(u'是否已预算')
    line_edit = fields.Boolean(u'明细是否可编辑')
    is_editable = fields.Boolean(u'可编辑')
    company_currency_id = fields.Many2one('res.currency', u'公司货币',
                                          default=lambda self: self.env.user.company_id.currency_id.id)
    company_currency_total_amount = fields.Monetary(u'本币合计', currency_field='company_currency_id', digits=(2, 4),compute=compute_total_amount_currency, store=True)
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
            'gongsi_id': self.gongsi_id.id,
        })
        self.payment_id = payment
        for one in self.expense_line_ids:
            one.state = 'confirmed'


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

    def btn_undo_confirm_force(self):
        self.expense_line_ids.btn_undo_confirm_force()

    def btn_match_budget(self):
        self.expense_line_ids.match_budget()

        self.is_budget = True

    def btn_release_budget(self):
        self.expense_line_ids.release_budget()
        self.is_budget = False



