# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning
from . comm import sfk_type

class account_payment_line(models.Model):
    _name = 'yjzy.account.payment.line'

    payment_id = fields.Many2one('yjzy.account.payment', u'付款单')
    payment_type = fields.Selection(related='payment_id.payment_type')
    currency_id = fields.Many2one('res.currency', related='payment_id.currency_id')
    product_id = fields.Many2one('product.product', u'产品')
    account_id = fields.Many2one('account.account', u'科目')
    amount = fields.Monetary(u'金额', currency_field='currency_id')
    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告')
    expense_id = fields.Many2one('hr.expense', u'费用')

    debit_account_id = fields.Many2one('account.account', u'debit科目')
    credit_account_id = fields.Many2one('account.account', u'credit科目')

    polar = fields.Selection([(1, '+'), (-1, '-')], u'正负号', required=True)

    # currency_id = fields.Many2one('res.currency', u'货币')

    @api.onchange('product_id')
    def onchange_product(self):
        payment_type = self.payment_id.payment_type
        if (not payment_type) or (not self.product_id):
            self.account_id = None
            self.polar = None
        else:
            if payment_type == 'inbound':
                self.account_id = self.product_id.property_account_income_id
                self.polar = -1
            elif payment_type == 'outbound':
                self.account_id = self.product_id.property_account_expense_id
                self.polar = 1
            else:
                self.account_id = self.product_id.property_account_expense_id
                self.polar = 1


class yjzy_account_payment(models.Model):
    _name = 'yjzy.account.payment'
    _inherit = 'account.payment'

    def default_name(self):
        ctx = self.env.context

        default_payment_type = ctx.get('default_payment_type')

        seq_code = 'yjzy.account.payment'

        if default_payment_type:
            seq_code += '.%s' % default_payment_type


        return self.env['ir.sequence'].sudo().next_by_code(seq_code)


    name = fields.Char(u'编号', default=lambda self: self.default_name())
    type = fields.Selection([('inout', u'收付款'), ('inner', u'内部'), ('renling', u'认领')], u'大类型')
    payment_type = fields.Selection(selection_add=[('claim_in', u'收款认领'), ('claim_out', u'付款认领')], string=u'类型')
    state = fields.Selection([('draft', u'草稿'), ('conformed', u'确认'), ('posted', u'过账'), ('done', u'完成')], u'State')
    expense_sheet_ids = fields.One2many('hr.expense.sheet', 'yjzy_payment_id', u'费用报告')
    payment_lines = fields.One2many('yjzy.account.payment.line', 'payment_id', u'明细')
    am_id = fields.Many2one('account.move', u'分录', copy=False)
    header_account_id = fields.Many2one('account.account', u'表头分录科目', store=True)
    polar = fields.Selection([(1, '+'), (-1, '-')], u'正负号', required=True, store=True)
    balance = fields.Float(u'余额', compute='compute_balance')
    yjzy_payment_id = fields.Many2one('account.payment', u'选收款单')
    yjzy_payment_currency_id = fields.Many2one('res.currency', related='yjzy_payment_id.currency_id')
    yjzy_payment_balance = fields.Monetary(u'认领余额', related='yjzy_payment_id.balance', currency_field='yjzy_payment_currency_id')
    need_split = fields.Boolean(u'拆分表头分录')
    is_renling = fields.Boolean(u'可以被认领')

    be_renling = fields.Boolean(u'是否认领单')
    sfk_type = fields.Selection(sfk_type, u'收付类型')

    @api.onchange('yjzy_payment_id')
    def onchange_yjzy_payment(self):
        if self.yjzy_payment_id:
            self.currency_id = self.yjzy_payment_id.currency_id
        else:
            self.currency_id = self.journal_id.currency_id



    def compute_balance(self):
        account_obj = self.env['account.account']
        aml_obj = self.env['account.move.line']
        for one in self:
            if one.payment_type in ['inbound'] and one.is_renling:

                account_code = one.payment_type == 'inbound' and '220301' or '112301'
                account_id = account_obj.search([('code', '=', account_code)], limit=1)
                if not account_id:
                    continue

                domain = [('yjzy_payment_id', '=', one.id), ('account_id', '=', account_id.id)]
                amlines = aml_obj.search(domain)
                one.balance = sum([-1 * x.amount_currency for x in amlines])

    @api.onchange('payment_type', 'journal_id', 'destination_journal_id')
    def onchange_payment_type(self):
        one = self
        header_account = None
        if one.payment_type == 'inbound' and one.journal_id:
            header_account = one.journal_id.default_debit_account_id
            one.polar = 1

        elif one.payment_type == 'outbound' and one.journal_id:
            header_account = one.journal_id.default_credit_account_id
            one.polar = -1

        elif one.payment_type == 'claim_in' and one.journal_id:
            header_account = one.journal_id.default_debit_account_id
            one.polar = 1

        elif one.payment_type == 'claim_out' and one.journal_id:
            header_account = one.journal_id.default_credit_account_id
            one.polar = -1

        elif one.payment_type == 'transfer' and one.journal_id:
            header_account = one.journal_id.default_credit_account_id
            one.polar = -1

        elif one.payment_type == 'outbound':
            if one.journal_id:
                header_account = one.journal_id.default_debit_account_id
                one.polar = 1
            if one.destination_journal_id:
                header_account = one.destination_journal_id.default_credit_account_id
                one.polar = -1

        one.header_account_id = header_account

    def set_name(self):
        pass

    def create_lines_by_sheets(self):
        line_obj = self.env['yjzy.account.payment.line']
        for expense in self.expense_sheet_ids.mapped('expense_line_ids'):
            line = line_obj.create({
                'payment_id': self.id,
                'product_id': expense.product_id.id,
                'amount': expense.total_amount,
                'sheet_id': expense.sheet_id.id,
                'currency_id': expense.currency_id.id,
                'expense_id': expense.id,
                'polar': 1,
            })
            line.onchange_product()

    def act_confirm(self):
        if self.am_id:
            raise Warning(u'请勿重复确认')
        move = self.create_account_move()
        move.post()
        self.state = 'conformed'

    def act_posted(self):
        self.state = 'posted'

    def _prepare_header_data(self, move, is_reversal=False):
        self.ensure_one()
        yjzy_payment_id = self.yjzy_payment_id.id or self.id
        amount_currency = self.amount * self.polar
        account_id = self.header_account_id.id
        if is_reversal:
            amount_currency *= -1
            account_id = self.destination_journal_id.default_debit_account_id.id
            if not account_id:
                raise Warning(u'日记账没有设置科目%s' % self.destination_journal_id)

        return {
            'account_id': account_id,
            'partner_id': self.partner_id.id,
            'amount_currency': amount_currency,
            'currency_id': self.currency_id.id,
            'move_id': move.id,
            'yjzy_payment_id': yjzy_payment_id,
            'new_payment_id': yjzy_payment_id,
        }

    def _prepare_line_data(self, line, move):
        self.ensure_one()
        yjzy_payment_id = self.yjzy_payment_id.id or self.id
        return {
            'account_id': line.account_id.id,
            'partner_id': self.partner_id.id,
            'move_id': move.id,
            'amount_currency': line.amount * line.polar,
            'currency_id': line.currency_id.id,
            'sheet_id': line.sheet_id.id,
            'expense_id': line.expense_id.id,
            'yjzy_payment_id': yjzy_payment_id,
            'new_payment_id': yjzy_payment_id,
        }

    def create_header_aml(self, move):
        self.ensure_one()
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)

        data = self._prepare_header_data(move)
        if not self.need_split:
            aml = aml_obj.create(data)
            aml._onchange_amount_currency()
        else:
            for line in self.payment_lines:
                data2 = data.copy()
                data2.update({'amount_currency': line.amount})
                aml2 = aml_obj.create(data2)
                aml2._onchange_amount_currency()

        return True

    def create_account_move(self):
        self.ensure_one()

        am_obj = self.env['account.move']
        aml_obj = self.env['account.move.line'].with_context(check_move_validity=False)

        move = self.am_id or am_obj.create({
            'journal_id': self.journal_id.id,
        })

        # 表头分录
        # aml1 = aml_obj.create(self._prepare_header_data(move))
        # aml1._onchange_amount_currency()
        self.create_header_aml(move)

        if self.payment_type == 'transfer':
            aml2 = aml_obj.create(self._prepare_header_data(move, is_reversal=True))
            aml2._onchange_amount_currency()

        # 明细分录
        if self.payment_type != 'transfer':
            for line in self.payment_lines:
                amline = aml_obj.create(self._prepare_line_data(line, move))
                amline._onchange_amount_currency()

        self.am_id = move

        return move

        # return {
        #     'name': u'分录',
        #     'res_model': 'account.move',
        #     'res_id': move.id,
        #     'view_type': 'form',
        #     "view_mode": 'form',
        #     'type': 'ir.actions.act_window',
        #     # 'target': 'new'
        # }
