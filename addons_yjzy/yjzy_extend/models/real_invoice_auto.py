# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree

class RealInvoiceAuto(models.Model):
    _name = 'real.invoice.auto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '实际发票'
    _order = 'id desc'

    api.depends('untaxed_amount','tax')
    def compute_amount_total(self):
        for one in self:
            amount_total = (1 + one.tax) * one.untaxed_amount
            one.amount_total = amount_total
    invoice_code = fields.Char(u'发票代码')
    invoice_number = fields.Char(u'发票号')
    partner_id = fields.Many2one('res.partner',u'合作伙伴')
    company_currency_id = fields.Many2one('res.currency','本币币种', default=lambda self: self.env.user.company_id.currency_id)
    untaxed_amount = fields.Monetary(u'不含税金额',currency_field='company_currency_id')
    tax = fields.Float(u'税率',default = 0.13)
    amount_total = fields.Monetary(u'含税金额',currency_field='company_currency_id',compute='compute_amount_total')
    data_invoice = fields.Date(u'开票日期')
    state = fields.Selection([('draft', 'draft'), ('done', 'done')], 'State', default='draft')

class PlanInvoiceAuto(models.Model):
    _name = 'plan.invoice.auto'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '应收发票'
    _order = 'id desc'

    @api.depends('bill_id','bill_id.hsname_all_ids')
    def compute_hs_name_all_ids(self):
        for one in self:
            print('akiny',one.bill_id.hsname_all_ids)
            one.hsname_all_ids = one.bill_id.hsname_all_ids

    def _default_plan_invoice_auto_name(self):
        invoice_tenyale_name = self.env.context.get('default_invoice_tenyale_name')
        if invoice_tenyale_name:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.%s' % invoice_tenyale_name)
        else:
            tenyale_name = self.env['ir.sequence'].next_by_code('account.invoice.tenyale_invoice')
        return tenyale_name

    name = fields.Char('name',default=lambda self: self.env['ir.sequence'].next_by_code('plan.invoice.auto.name'))
    invoice_id = fields.Many2one('account.invoice','应付账单')
    bill_id = fields.Many2one('transport.bill','出运合同',related='invoice_id.bill_id',store=True)
    hsname_all_ids = fields.Many2many('tbl.hsname.all','报关明细',compute='compute_hs_name_all_ids')
    state = fields.Selection([('draft','draft'),('done','done')],'State',default='draft')
    include_tax = fields.Boolean('含税',related='invoice_id.include_tax')





#####################################################################################################################
