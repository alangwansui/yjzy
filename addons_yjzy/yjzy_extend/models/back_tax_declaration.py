# -*- coding: utf-8 -*-

from odoo import fields, models, api, _
from odoo.exceptions import Warning
from odoo.addons import decimal_precision as dp
from lxml import etree

class DeclareDeclaration(models.Model):
    _name = 'back.tax.declaration'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '报关申报表'
    _order = 'id desc'


    @api.depends('btd_line_ids','btd_line_ids.invoice_amount_total')
    def compute_invoice_amount_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            invoice_amount_all = sum(x.invoice_amount_total for x in btd_line_ids)
            one.invoice_amount_all = invoice_amount_all

    @api.depends('btd_line_ids', 'btd_line_ids.invoice_residual_total')
    def compute_invoice_residual_all(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            invoice_residual_all = sum(x.invoice_residual_total for x in btd_line_ids)
            one.invoice_residual_all = invoice_residual_all

    @api.depends('btd_line_ids', 'btd_line_ids.declaration_amount')
    def compute_declaration_amount(self):
        for one in self:
            btd_line_ids = one.btd_line_ids
            declaration_amount_all = sum(x.declaration_amount for x in btd_line_ids)
            one.declaration_amount_all = declaration_amount_all


    @api.depends('reconcile_order_ids','reconcile_order_ids.amount_total_org_new')
    def compute_reconcile_amount(self):
        for one in self:
            reconcile_amount = sum(x.amount_total_org_new for x in one.reconcile_order_ids)
            declaration_amount_all = one.declaration_amount_all
            one.reconcile_amount = reconcile_amount
            one.declaration_amount_all_residual = declaration_amount_all - reconcile_amount

    @api.depends('btd_line_ids','btd_line_ids.declaration_amount_residual')
    def compute_declaration_amount_all_residual_new(self):
        for one in self:
            declaration_amount_all_residual_new = sum(x.declaration_amount_residual for x in one.btd_line_ids)
            one.declaration_amount_all_residual_new = declaration_amount_all_residual_new


    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('back.tax.declaration'))
    btd_line_ids = fields.One2many('back.tax.declaration.line','btd_id',u'申报明细')
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    state = fields.Selection([('draft',u'草稿'),('done',u'确认'),('paid',u'已收款'),('cancel',u'取消')],'State', default='draft')
    company_currency_id = fields.Many2one('res.currency', string='公司货币', related='company_id.currency_id',
                                          readonly=True)
    declaration_date = fields.Date('申报日期')
    invoice_amount_all = fields.Monetary(u'原始应收退税',currency_field='company_currency_id',compute=compute_invoice_amount_all, store=True)
    invoice_residual_all = fields.Monetary(u'剩余应收退税',currency_field='company_currency_id',compute=compute_invoice_residual_all,store=True)
    declaration_amount_all = fields.Monetary(u'本次申报金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)
    declaration_amount_all_residual_new = fields.Monetary(u'本次申报金额', currency_field='company_currency_id',
                                             compute=compute_declaration_amount_all_residual_new, store=True)
    company_id = fields.Many2one('res.company', string='Company',required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)
    reconcile_order_ids = fields.One2many('account.reconcile.order','back_tax_declaration_id','核销单')
    reconcile_amount = fields.Monetary('收款认领金额',currency_field='company_currency_id',compute=compute_reconcile_amount,store=True)
    declaration_amount_all_residual = fields.Monetary(u'本次申报金额收款金额',currency_field='company_currency_id',compute=compute_declaration_amount,store=True)

    @api.multi
    def name_get(self):
        res = []
        for one in self:
            name = '%s:%s' % (one.name, one.declaration_amount_all)
            res.append((one.id, name))
        return res


    def action_confirm(self):
        self.state = 'done'
        invoice_ids = self.btd_line_ids.mapped('invoice_id')
        for one in invoice_ids:
            one.back_tax_declaration_state = '20'


    def action_cancel(self):
        invoice_paid_lines = self.btd_line_ids.filtered(lambda x:x.invoice_id.state == 'paid' and x.invoice_id.yjzy_type == 'back_tax')
        if len(invoice_paid_lines) !=0:
            raise Warning('已经收款认领，不允许取消申报单！')
        else:
            self.state = 'draft'
            self.btd_line_ids.mapped('invoice_id').back_tax_declaration_state = '10'



    def open_wizard_back_tax_declaration(self):
        self.ensure_one()
        ctx = self.env.context.copy()

        ctx.update({
            'default_gongsi_id': self.gongsi_id.id,

        })
        return {
            'name': '添加应收退税账单',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'wizard.back.tax.declaration',
            'target': 'new',
            'type': 'ir.actions.act_window',

            'context': ctx,
        }

class DeclareDeclarationLine(models.Model):
    _name = 'back.tax.declaration.line'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = '退税申报明细'
    _order = 'id desc'

    @api.depends('invoice_id','invoice_id.amount_total')
    def compute_invoice_amount_total(self):
        for one in self:
            one.invoice_amount_total = one.invoice_id.amount_total


    @api.depends('invoice_id', 'invoice_id.residual')
    def compute_invoice_residual(self):
        for one in self:
            one.invoice_residual_total = one.invoice_id.residual

    @api.depends('declaration_amount','invoice_residual_total','declaration_amount')
    def compute_declaration_amount_residual(self):
        for one in self:
            declaration_amount_residual = one.declaration_amount - (one.invoice_amount_total - one.invoice_residual_total)
            one.declaration_amount_residual = declaration_amount_residual

    btd_id = fields.Many2one('back.tax.declaration',u'退税申报单',ondelete='cascade',  required=True)
    invoice_id = fields.Many2one('account.invoice',u'账单', required=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    invoice_amount_total = fields.Monetary(u'账单原始金额',currency_field='invoice_currency_id',compute=compute_invoice_amount_total,store=True)
    invoice_residual_total = fields.Monetary(u'账单剩余金额',currency_field='invoice_currency_id',compute=compute_invoice_residual,store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='btd_id.company_id', store=True, readonly=True, related_sudo=False)
    declaration_amount = fields.Monetary(u'退税申报金额',currency_field='invoice_currency_id')
    declaration_amount_residual = fields.Monetary(u'未收款申报金额',currency_field='invoice_currency_id',compute=compute_declaration_amount_residual,store=True)
    comments = fields.Text(u'备注')












#####################################################################################################################
