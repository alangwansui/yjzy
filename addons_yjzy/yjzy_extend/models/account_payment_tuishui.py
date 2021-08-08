# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import Warning
from odoo.addons.account.models.account_payment import account_payment as Account_Payment
from .comm import sfk_type, invoice_attribute_all_in_one
from odoo.addons import decimal_precision as dp
from datetime import datetime, timedelta


class AccountPayment(models.Model):
    _inherit = "account.payment"
    # _order = "sequence"

    back_tax_declaration_id = fields.Many2one('back.tax.declaration', u'退税申报')
    btd_line_ids = fields.One2many('back.tax.declaration.line', 'tuishuirld_id', u'申报明细')
    declaration_title = fields.Char(u'申报说明', related='back_tax_declaration_id.declaration_title')
    declaration_date = fields.Date(u'申报日期', related='back_tax_declaration_id.declaration_date')
    declaration_amount_all = fields.Monetary(u'本次申报金额', currency_field='currency_id',related='back_tax_declaration_id.declaration_amount_all')
    back_tax_declaration_name = fields.Char(u'编号', related='back_tax_declaration_id.name', store=True)
    declaration_state = fields.Selection(
        [('draft', u'草稿'), ('approval', '审批中'), ('done', u'确认'), ('paid', u'已收款'), ('cancel', u'取消')], 'State',
        relate='back_tax_declaration_id.state')
    rcsktsrld_ids = fields.One2many('account.payment','tuishuirld_id',u'收款退税认领',domain=[('sfk_type','=','rcsktsrld')])
    tuishuirld_id = fields.Many2one('account.payment',u'退税申报认领单')
    tuishuirld_currency_id = fields.Many2one('res.currency', related='tuishuirld_id.currency_id')
    tuishuirld_amount = fields.Monetary(u'退税申报认领金额',currency_field='tuishuirld_currency_id',related='tuishuirld_id.amount')


    def open_back_tax_declaration_id(self):

        form_view = self.env.ref('yjzy_extend.view_back_tax_declaration_form').id
        return {
            'name': '退税申报表',
            'view_type': 'form',
            'view_mode': 'tree,form',
            'res_model': 'account.reconcile.order',
            'views': [(form_view, 'form')],
            'target': 'current',
            'type': 'ir.actions.act_window',
            'domain': [('yjzy_advance_payment_id', '=', self.id)],
            'context': {
                        }

        }