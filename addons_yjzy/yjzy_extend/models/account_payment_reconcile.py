# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type

Option_Add = [
    ('advance', u'预收付'),
    ('date_after_ship', u'客户交单后的天数'),
    ('date_after_finish', u'供应商交单日期'),
]




class account_payment(models.Model):
    _inherit = 'account.payment'

    def compute_advance_balance_aml_total(self):
        for one in self:
            advance_balance_aml_total = 0
            all_lines = one.aml_advace_ids
            if one.sfk_type == 'ysrld':
                lines = all_lines.filtered(lambda x: x.account_id.code == '2203')
                if one.currency_id.name == 'CNY':
                    advance_balance_aml_total = sum([x.credit - x.debit for x in lines])
                else:
                    advance_balance_aml_total = sum([-1 * x.amount_currency for x in lines])
            if one.sfk_type == 'yfsqd':
                lines = all_lines.filtered(lambda x: x.account_id.code == '1123')
                if one.currency_id.name == 'CNY':
                    advance_balance_aml_total = sum([-1 * (x.credit - x.debit) for x in lines])
                else:
                    advance_balance_aml_total = sum([1 * x.amount_currency for x in lines])

            one.advance_balance_aml_total = advance_balance_aml_total
            # if advance_balance_aml_total == 0 and one.state_1 == '50_posted':
            #     one.state_1 = '60_done'
            #     one.test_reconcile()
            #     one.write({'state': 'reconciled'})
    def compute_payment_ids_count(self):
        for one in self:
            payment_ids_count= len(one.payment_ids)
            one.payment_ids_count = payment_ids_count


    payment_ids_count = fields.Integer(u'预收认领预付申请数量', compute=compute_payment_ids_count)

    reconcile_ysrld_ids = fields.One2many('account.payment','yjzy_payment_id',u'预收核销',)#domain=[('sfk_type','=','reconcile_ysrld')]

    reconcile_type_reconcile = fields.Selection([('payment_in',u'收款单核销'),
                                       ('payment_out',u'付款单核销'),
                                       ('advance_payment_in',u'预收款核销'),
                                       ('advance_payment_out',u'预付款单核销'),
                                       ('invoice_customer',u'应收核销'),
                                       ('invoice_supplier',u'应付核销'),],u'核销类型')#付款单核销注意付款申请单和付款指令两个，应该是对付款申请单进行核销

    aml_advace_ids = fields.One2many('account.move.line', 'new_advance_payment_id', u'预收付余额相关分录')
    advance_balance_aml_total = fields.Monetary(u'预收余额', compute=compute_advance_balance_aml_total, currency_field='yjzy_payment_currency_id',)

    yjzy_payment_advance_balance = fields.Monetary(u'未完成认领金额', related='yjzy_payment_id.advance_balance_total', currency_field='yjzy_payment_currency_id')





    #创建核销单
    def create_reconcile(self):
        form_view = self.env.ref('yjzy_extend.view_ysrld_reconcile_form')
        ctx = {}
        partner = self.partner_id
        if self.sfk_type == 'ysrld':
            # partner = self.env['res.partner'].search([('name', '=', u'未定义')], limit=1)
            so_id = self.so_id

            advance_account_id = self.env['account.account'].search([('code','=','5609'),('company_id', '=', self.env.user.company_id.id)])
            ctx = { 'show_shoukuan': True,
                    'default_sfk_type': 'reconcile_ysrld',
                    'default_payment_type': 'inbound',
                    'default_be_renling': True,
                    'default_advance_ok': True,
                    'default_partner_type': 'customer',
                    'default_partner_id':partner.id,
                    'default_yjzy_payment_id':self.id,
                    'default_advance_account_id':advance_account_id.id,
                    'default_reconcile_type': '50_reconcile',

                    'default_so_id':so_id.id}
        if self.sfk_type == 'yfsqd':
            # partner = self.env['res.partner'].search([('name', '=', u'未定义')], limit=1)
            po_id = self.po_id
            advance_account_id = self.env['account.account'].search(
                [('code', '=', '5609'), ('company_id', '=', self.env.user.company_id.id)])
            ctx = {'show_shoukuan': True,
                   'default_sfk_type': 'reconcile_yfsqd',
                   'default_payment_type': 'outbound',
                   'default_be_renling': True,
                   'default_advance_ok': True,
                   'default_partner_type': 'supplier',
                   'default_partner_id': partner.id,
                   'default_yjzy_payment_id': self.id,
                   'default_advance_account_id': advance_account_id.id,
                   'default_reconcile_type': '50_reconcile',
                   'default_po_id': po_id.id}
        return {
            'name':u'核销单',
            'view_type':'form',
            'view_mode':'form',
            'type':'ir.actions.act_window',
            'res_model':'account.payment',
            'views':[(form_view.id,'form')],
            'target':'new',
            'context':ctx
        }


