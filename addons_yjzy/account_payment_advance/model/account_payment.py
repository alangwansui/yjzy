# -*- coding: utf-8 -*-
# Copyright 2016 Konos <info@konos.cl>
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).

import logging
from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.safe_eval import safe_eval as eval


class AccountPayment(models.Model):
    _inherit = "account.payment"


    def _default_advance_account(self):
        ctx = self.env.context
        print('===ctx', ctx)

        sfk_type = ctx.get('default_sfk_type', '')

        if sfk_type == 'rcskd':
            account = self.env['account.account'].search([('code', '=', '220301')], limit=1)
            return account.id
        elif sfk_type == 'rcfkd':
            account = self.env['account.account'].search([('code', '=', '112301')], limit=1)
            return account.id
        elif sfk_type == 'ysrld':
            account = self.env['account.account'].search([('code', '=', '2203')], limit=1)
            return account.id
        elif sfk_type == 'jiehui':

            return False


        if ctx.get('default_advance_ok'):
            if ctx.get('default_partner_type', '') == 'supplier':
                account = self.env['account.account'].search([('code', '=', '1123')], limit=1)
                return account.id
            if ctx.get('default_partner_type', '') == 'customer':
                account = self.env['account.account'].search([('code', '=', '2203')], limit=1)
                return account.id
        else:
            return



    advance_ok = fields.Boolean(
        string=u'是预付',
        help="Select if you want to establish a features of advance")
    advance_account_id = fields.Many2one('account.account',
        string=u"预付科目",
        domain="[('deprecated', '=', False)]",
        default=lambda self: self._default_advance_account(),
        help="This account will be used instead of the default one as the receivable account for the current partner")


    @api.one
    @api.depends('invoice_ids', 'payment_type', 'partner_type', 'partner_id')
    def _compute_destination_account_id(self):
        """ inherited and overwrite original method
            Add the condition that evaluates if exists account advance and it placed as has account destiny if condition applied.
        """
        if self.invoice_ids:
            self.destination_account_id = self.advance_ok and self.advance_account_id.id or self.invoice_ids[0].account_id.id
        elif self.payment_type == 'transfer':
            if not self.company_id.transfer_account_id.id:
                raise UserError(_('Transfer account not defined on the company.'))
            self.destination_account_id = self.advance_ok and self.advance_account_id.id or self.company_id.transfer_account_id.id
        elif self.partner_id:
            if self.partner_type == 'customer':
                self.destination_account_id = self.advance_ok and self.advance_account_id.id or self.partner_id.property_account_receivable_id.id
            else:
                self.destination_account_id = self.advance_ok and self.advance_account_id.id or self.partner_id.property_account_payable_id.id



    @api.onchange('partner_id')
    def _onchange_partner_id(self):
        if self.payment_type == 'inbound':
            self.advance_account_id = self.partner_id.property_account_receivable_id.id
        elif self.payment_type == 'outbound':
            self.advance_account_id = self.partner_id.property_account_payable_id.id



    @api.onchange('payment_type')
    def _onchange_payment_type(self):
        res = self._onchange_partner_id()
        if self.payment_type:
            return {'domain': {'payment_method': [('payment_type', '=', self.payment_type)]}}  