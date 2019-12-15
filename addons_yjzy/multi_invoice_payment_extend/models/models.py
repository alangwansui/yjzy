# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.addons.account.models.account_payment import MAP_INVOICE_TYPE_PAYMENT_SIGN

class account_register_payments(models.TransientModel):
    _inherit = 'account.register.payments'

    def default_lines(self):
        ctx = self.env.context
        print (self.env.context)

        active_model = ctx.get('active_model')
        active_ids = ctx.get('active_ids')

        line_obj = self.env['account.register.payments.line']
        lines = self.env['account.register.payments.line']
        if active_model ==  'account.invoice':
            for invoice in self.env[active_model].browse(active_ids):
                line = line_obj.create({
                    'main_id': self.id,
                    'invoice_id': invoice.id,
                    'amount':  MAP_INVOICE_TYPE_PAYMENT_SIGN[invoice.type] * invoice.residual_company_signed,
                })
                lines |= line
        return lines

    line_ids = fields.One2many('account.register.payments.line',  'main_id', u'明细', default=lambda self:self.default_lines())

    @api.onchange('line_ids', 'line_ids.amount')
    def onchange_lines(self):
        print('==change_lines')
        total  = 0.0
        for line in self.line_ids:
            #invoice = line.invoice_id
            total += line.amount
        print ('===')
        self.amount = total






class account_register_payments_line(models.TransientModel):
    _name = 'account.register.payments.line'


    @api.depends('invoice_id', 'amount', 'currency_id')
    def _compute_payment_difference(self):
        for one in self:
            one.payment_difference = one.residual_signed - one.amount

    main_id  = fields.Many2one('account.register.payments', u'主单')
    invoice_id = fields.Many2one('account.invoice', u'发票')
    currency_id = fields.Many2one('res.currency', related='invoice_id.currency_id')
    residual_signed = fields.Monetary(related='invoice_id.residual_signed')
    amount = fields.Float(u'付款金额')

    payment_difference = fields.Monetary(compute='_compute_payment_difference', readonly=True)
    payment_difference_handling = fields.Selection([('open', 'Keep open'), ('reconcile', 'Mark invoice as fully paid')], default='open', string="Payment Difference", copy=False)
    writeoff_account_id = fields.Many2one('account.account', string="Difference Account", domain=[('deprecated', '=', False)], copy=False)
    writeoff_label = fields.Char(
        string='Journal Item Label',
        help='Change label of the counterpart that will hold the payment difference',
        default='Write-Off')


