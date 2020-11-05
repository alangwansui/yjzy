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


    name = fields.Char('编号', default=lambda self: self.env['ir.sequence'].next_by_code('back.tax.declaration'))
    btd_line_ids = fields.One2many('back.tax.declaration.line','btd_id',u'申报明细')
    gongsi_id = fields.Many2one('gongsi', '内部公司')
    state = fields.Selection([('draft',u'草稿'),('done',u'确认'),('paid',u'已收款'),('cancel',u'取消')],'State', default='draft')
    declaration_date = fields.Date('申报日期')
    invoice_amount_all = fields.Float(u'原始应收退税',compute=compute_invoice_amount_all,store=True)
    invoice_residual_all = fields.Float(u'剩余应收退税',compute=compute_invoice_residual_all,store=True)
    declaration_amount_all = fields.Float(u'本次申报金额',compute=compute_declaration_amount,store=True)
    company_id = fields.Many2one('res.company', string='Company',required=True, readonly=True,
                                 default=lambda self: self.env.user.company_id.id)


    def action_confirm(self):
        self.state = 'done'
        self.btd_line_ids.mapped('invoice_id').back_tax_declaration_state = '20'


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

    btd_id = fields.Many2one('back.tax.declaration',u'退税申报单',ondelete='cascade',  required=True)
    invoice_id = fields.Many2one('account.invoice',u'账单', required=True)
    invoice_currency_id = fields.Many2one('res.currency', u'交易货币', related='invoice_id.currency_id', readonly=True)
    invoice_amount_total = fields.Monetary(u'账单原始金额',currency_field='invoice_currency_id',compute=compute_invoice_amount_total,store=True)
    invoice_residual_total = fields.Monetary(u'账单剩余金额',currency_field='invoice_currency_id',compute=compute_invoice_residual,store=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 related='btd_id.company_id', store=True, readonly=True, related_sudo=False)
    declaration_amount = fields.Monetary(u'退税申报金额',currency_field='invoice_currency_id')
    comments = fields.Text(u'备注')












#####################################################################################################################
