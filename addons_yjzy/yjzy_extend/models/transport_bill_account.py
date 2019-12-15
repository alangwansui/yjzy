# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning


class transport_bill_account(models.Model):
    _name = 'transport.bill.account'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = u'出运报关金额'
    _order = 'id desc'

    def default_currency(self):
        return self.env.ref('base.USD').id

    def compute_amount(self):
        account_public1, account_public2, account_private1, account_private2, account_rmb3, account_diff = self.env[
            'transport.bill'].get_account_by_config_parameter()

        for one in self:
            #TODO 根据分录明细计算金额
            lines = one.line_ids
            ## 对明细（发运单） 金额的累加
            one.sale_amount = sum([x.org_sale_amount for x in lines])
            one.ciq_amount = sum([x.ciq_amount for x in lines])
            one.no_ciq_amount = sum([x.no_ciq_amount for x in lines])
            one.amount_public1 = sum([x.amount_public1 for x in lines])
            one.amount_public2 = sum([x.amount_public2 for x in lines])
            one.amount_private1 = sum([x.amount_private1 for x in lines])
            one.amount_private2 = sum([x.amount_private2 for x in lines])
            one.amount_rmb3 = sum([x.amount_rmb3 for x in lines])
            one.amount_diff = sum([x.amount_diff for x in lines])
            one.amount_received = sum([x.amount_received for x in lines])
            one.amount_real_payment = sum([x.amount_real_payment for x in lines])
            one.amount_account_payment = sum([x.amount_account_payment for x in lines])
            one.amount_account_adjust = sum([x.amount_account_adjust for x in lines])

            # 统计内部转账金额
            # 报关金额 - 美金账户11 —  内部转账统计：借方是美金账户11
            # 不报关金额 - 人民币15  -  内部转账统计：借方是人民币3B
            settlement1, settlement2 = 0, 0
            for line in one.inner_payment_ids.mapped('move_line_ids'):
                if line.account_id == account_public2:
                    settlement1 += line.company_currency_id.compute(line.debit - line.credit, one.currency_id)
                if line.account_id == account_rmb3:
                    settlement2 += line.company_currency_id.compute(line.debit - line.credit, one.currency_id)

            #结算后账户1       =     报关金额    -     美元账户11    -    内部转账统计：借方是美金账户11
            one.amount_settlement1 = one.ciq_amount - one.amount_public2 - settlement1
            #结算后账户2       =     不报关金额   -    人民币账户15   -    内部转账统计：借方是人民币3B
            one.amount_settlement2 = one.no_ciq_amount - one.amount_private1 - settlement2

    name = fields.Char('编号', reuired=True, default=lambda self: self.env['ir.sequence'].next_by_code('transport.bill.account'))
    date = fields.Date(u'日期', default=lambda self: fields.date.today())
    state = fields.Selection([('draft', u'草稿'), ('confirmed', u'已确认'), ('done', u'完成')], u'状态', default='draft')
    currency_id = fields.Many2one('res.currency', u'交易货币',  required=True, default=lambda self: self.default_currency())
    line_ids = fields.One2many('transport.bill', 'tba_id', u'明细')
    inner_payment_ids = fields.One2many('account.payment', 'tba_id', u'内部转账')

    sale_amount = fields.Monetary(u'销售金额', compute=compute_amount, currency_field='currency_id')
    ciq_amount = fields.Monetary(u'报关金额', compute=compute_amount, currency_field='currency_id')
    no_ciq_amount = fields.Monetary(u'不报关金额', compute=compute_amount, currency_field='currency_id')
    amount_public1 = fields.Monetary(u'美元账户1', compute=compute_amount, currency_field='currency_id')
    amount_public2 = fields.Monetary(u'美元账户11', compute=compute_amount, currency_field='currency_id')
    amount_private1 = fields.Monetary(u'人民币账户15', compute=compute_amount, currency_field='currency_id')
    amount_private2 = fields.Monetary(u'人民币账户13', compute=compute_amount, currency_field='currency_id')
    amount_rmb3 = fields.Monetary(u'人民币3B', compute=compute_amount, currency_field='currency_id')
    amount_diff = fields.Monetary(u'差异处理', compute=compute_amount, currency_field='currency_id')
    amount_received = fields.Monetary(u'合计收款', compute=compute_amount, currency_field='currency_id')
    amount_real_payment = fields.Monetary(u'实际支付11', compute=compute_amount, currency_field='currency_id')
    amount_real_payment_beginning = fields.Monetary(u'账户11期初', compute=compute_amount, currency_field='currency_id')
    amount_account_payment = fields.Monetary(u'支付账户3B', compute=compute_amount, currency_field='currency_id')
    amount_account_adjust = fields.Monetary(u'账户调节', compute=compute_amount, currency_field='currency_id')
    amount_settlement1 = fields.Monetary(u'结算后账户11', compute=compute_amount, currency_field='currency_id')
    amount_settlement2 = fields.Monetary(u'结算后账户3B', compute=compute_amount, currency_field='currency_id')


    #
    move_line_ids = fields.Many2many('account.move.line', 'ref_tba_aml', 'bid', 'lid', u'相关分录明细', compute='compute8lines')

    last_amount = fields.Float('上次核销剩余金额', compute='compute_last_amount')

    def compute_last_amount(self):
        for one in self:
            last_record = self.search([('id', '!=', one.id)], limit=1, order='id desc')
            one.last_amount = last_record.amount_settlement1

    def _check(self):
        if len(self.line_ids.mapped('sale_invoice_id').mapped('currency_id')) > 1:
            raise Warning(u'所有明细必须是同一币种')

    @api.depends('line_ids')
    def compute8lines(self):
        self.ensure_one()
        if self.line_ids:
            invoices = self.line_ids.mapped('sale_invoice_id')
            lines = invoices.mapped('move_line_ids')
            self.move_line_ids = lines
            self.currency_id = self.line_ids[0].sale_currency_id

    def get_payment_info(self):
        self.ensure_one()
        self._check()
        self.line_ids.with_context(date=self.date).get_payment_info()

    def open_account_payments_transfer(self):
        ctx = self._context.copy()
        ctx.update({'default_payment_type': 'transfer', 'default_tba_id': self.id})
        return {
            'type': 'ir.actions.act_window',
            'name': '内部转账',
            'res_model': 'account.payment',
            'target': 'selft',
            'view_mode': 'form',
            'context': ctx,
        }
