# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.exceptions import Warning


class account_move(models.Model):
    _inherit = 'account.move'

    reconcile_order_id = fields.Many2one('account.reconcile.order', u'核销单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    bill_id = fields.Many2one('transport.bill', u'发运单', related='invoice_id.bill_id')
    include_tax = fields.Boolean(u'含税', related='bill_id.include_tax')
    tb_contract_code = fields.Char(u'出运合同号', related='bill_id.ref')

    purchase_contract_code = fields.Char(u'采购合同号')

    gongsi_id = fields.Many2one('gongsi', '内部公司')



    @api.multi
    def post(self):
        res = super(account_move, self).post()
        return res

class account_move_line(models.Model):
    _inherit = 'account.move.line'

    so_id = fields.Many2one('sale.order', u'销售订单')
    po_id = fields.Many2one('purchase.order', u'采购订单')

    plan_invoice_id = fields.Many2one('account.invoice', u'核销安排的发票')
    yjzy_payment_id = fields.Many2one('yjzy.account.payment', u'新收付款')

    
    sheet_id = fields.Many2one('hr.expense.sheet', u'费用报告')
    expense_id = fields.Many2one('hr.expense', u'费用')

    hx_code = fields.Char(u'内部核对标记', related='expense_id.hx_code', store=True, index=True)

    new_payment_id = fields.Many2one('account.payment', u'收付款ID')

    gongsi_id = fields.Many2one('gongsi', '内部公司')



    # @api.model
    # def create(self, vals):
    #     raise Exception('xxx')






    def get_amount_to_currency(self, to_currency, date=False):
        self.ensure_one()
        ctx = {}
        date = date or self.date
        ctx.update({'date': date})
        if self.amount_currency:
            amount = self.currency_id.with_context(ctx).compute(self.amount_currency, to_currency)
        else:
            amount = self.company_currency_id.with_context(ctx).compute(self.debit - self.credit, to_currency)
        return amount







